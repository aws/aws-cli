import pytest

from xdist.remote import Producer
from xdist.workermanage import NodeManager
from xdist.scheduler import (
    EachScheduling,
    LoadScheduling,
    LoadScopeScheduling,
    LoadFileScheduling,
    LoadGroupScheduling,
)


from queue import Empty, Queue


class Interrupted(KeyboardInterrupt):
    """signals an immediate interruption."""


class DSession:
    """A pytest plugin which runs a distributed test session

    At the beginning of the test session this creates a NodeManager
    instance which creates and starts all nodes.  Nodes then emit
    events processed in the pytest_runtestloop hook using the worker_*
    methods.

    Once a node is started it will automatically start running the
    pytest mainloop with some custom hooks.  This means a node
    automatically starts collecting tests.  Once tests are collected
    it will wait for instructions.
    """

    def __init__(self, config):
        self.config = config
        self.log = Producer("dsession", enabled=config.option.debug)
        self.nodemanager = None
        self.sched = None
        self.shuttingdown = False
        self.countfailures = 0
        self.maxfail = config.getvalue("maxfail")
        self.queue = Queue()
        self._session = None
        self._failed_collection_errors = {}
        self._active_nodes = set()
        self._failed_nodes_count = 0
        self._max_worker_restart = get_default_max_worker_restart(self.config)
        # summary message to print at the end of the session
        self._summary_report = None
        self.terminal = config.pluginmanager.getplugin("terminalreporter")
        if self.terminal:
            self.trdist = TerminalDistReporter(config)
            config.pluginmanager.register(self.trdist, "terminaldistreporter")

    @property
    def session_finished(self):
        """Return True if the distributed session has finished

        This means all nodes have executed all test items.  This is
        used by pytest_runtestloop to break out of its loop.
        """
        return bool(self.shuttingdown and not self._active_nodes)

    def report_line(self, line):
        if self.terminal and self.config.option.verbose >= 0:
            self.terminal.write_line(line)

    @pytest.hookimpl(trylast=True)
    def pytest_sessionstart(self, session):
        """Creates and starts the nodes.

        The nodes are setup to put their events onto self.queue.  As
        soon as nodes start they will emit the worker_workerready event.
        """
        self.nodemanager = NodeManager(self.config)
        nodes = self.nodemanager.setup_nodes(putevent=self.queue.put)
        self._active_nodes.update(nodes)
        self._session = session

    @pytest.hookimpl
    def pytest_sessionfinish(self, session):
        """Shutdown all nodes."""
        nm = getattr(self, "nodemanager", None)  # if not fully initialized
        if nm is not None:
            nm.teardown_nodes()
        self._session = None

    @pytest.hookimpl
    def pytest_collection(self):
        # prohibit collection of test items in controller process
        return True

    @pytest.hookimpl(trylast=True)
    def pytest_xdist_make_scheduler(self, config, log):
        dist = config.getvalue("dist")
        schedulers = {
            "each": EachScheduling,
            "load": LoadScheduling,
            "loadscope": LoadScopeScheduling,
            "loadfile": LoadFileScheduling,
            "loadgroup": LoadGroupScheduling,
        }
        return schedulers[dist](config, log)

    @pytest.hookimpl
    def pytest_runtestloop(self):
        self.sched = self.config.hook.pytest_xdist_make_scheduler(
            config=self.config, log=self.log
        )
        assert self.sched is not None

        self.shouldstop = False
        while not self.session_finished:
            self.loop_once()
            if self.shouldstop:
                self.triggershutdown()
                raise Interrupted(str(self.shouldstop))
        return True

    def loop_once(self):
        """Process one callback from one of the workers."""
        while 1:
            if not self._active_nodes:
                # If everything has died stop looping
                self.triggershutdown()
                raise RuntimeError("Unexpectedly no active workers available")
            try:
                eventcall = self.queue.get(timeout=2.0)
                break
            except Empty:
                continue
        callname, kwargs = eventcall
        assert callname, kwargs
        method = "worker_" + callname
        call = getattr(self, method)
        self.log("calling method", method, kwargs)
        call(**kwargs)
        if self.sched.tests_finished:
            self.triggershutdown()

    #
    # callbacks for processing events from workers
    #

    def worker_workerready(self, node, workerinfo):
        """Emitted when a node first starts up.

        This adds the node to the scheduler, nodes continue with
        collection without any further input.
        """
        node.workerinfo = workerinfo
        node.workerinfo["id"] = node.gateway.id
        node.workerinfo["spec"] = node.gateway.spec

        self.config.hook.pytest_testnodeready(node=node)
        if self.shuttingdown:
            node.shutdown()
        else:
            self.sched.add_node(node)

    def worker_workerfinished(self, node):
        """Emitted when node executes its pytest_sessionfinish hook.

        Removes the node from the scheduler.

        The node might not be in the scheduler if it had not emitted
        workerready before shutdown was triggered.
        """
        self.config.hook.pytest_testnodedown(node=node, error=None)
        if node.workeroutput["exitstatus"] == 2:  # keyboard-interrupt
            self.shouldstop = f"{node} received keyboard-interrupt"
            self.worker_errordown(node, "keyboard-interrupt")
            return
        if node in self.sched.nodes:
            crashitem = self.sched.remove_node(node)
            assert not crashitem, (crashitem, node)
        self._active_nodes.remove(node)

    def worker_internal_error(self, node, formatted_error):
        """
        pytest_internalerror() was called on the worker.

        pytest_internalerror() arguments are an excinfo and an excrepr, which can't
        be serialized, so we go with a poor man's solution of raising an exception
        here ourselves using the formatted message.
        """
        self._active_nodes.remove(node)
        try:
            assert False, formatted_error
        except AssertionError:
            from _pytest._code import ExceptionInfo

            excinfo = ExceptionInfo.from_current()
            excrepr = excinfo.getrepr()
            self.config.hook.pytest_internalerror(excrepr=excrepr, excinfo=excinfo)

    def worker_errordown(self, node, error):
        """Emitted by the WorkerController when a node dies."""
        self.config.hook.pytest_testnodedown(node=node, error=error)
        try:
            crashitem = self.sched.remove_node(node)
        except KeyError:
            pass
        else:
            if crashitem:
                self.handle_crashitem(crashitem, node)

        self._failed_nodes_count += 1
        maximum_reached = (
            self._max_worker_restart is not None
            and self._failed_nodes_count > self._max_worker_restart
        )
        if maximum_reached:
            if self._max_worker_restart == 0:
                msg = "worker {} crashed and worker restarting disabled".format(
                    node.gateway.id
                )
            else:
                msg = "maximum crashed workers reached: %d" % self._max_worker_restart
            self._summary_report = msg
            self.report_line("\n" + msg)
            self.triggershutdown()
        else:
            self.report_line("\nreplacing crashed worker %s" % node.gateway.id)
            self.shuttingdown = False
            self._clone_node(node)
        self._active_nodes.remove(node)

    @pytest.hookimpl
    def pytest_terminal_summary(self, terminalreporter):
        if self.config.option.verbose >= 0 and self._summary_report:
            terminalreporter.write_sep("=", f"xdist: {self._summary_report}")

    def worker_collectionfinish(self, node, ids):
        """worker has finished test collection.

        This adds the collection for this node to the scheduler.  If
        the scheduler indicates collection is finished (i.e. all
        initial nodes have submitted their collections), then tells the
        scheduler to schedule the collected items.  When initiating
        scheduling the first time it logs which scheduler is in use.
        """
        if self.shuttingdown:
            return
        self.config.hook.pytest_xdist_node_collection_finished(node=node, ids=ids)
        # tell session which items were effectively collected otherwise
        # the controller node will finish the session with EXIT_NOTESTSCOLLECTED
        self._session.testscollected = len(ids)
        self.sched.add_node_collection(node, ids)
        if self.terminal:
            self.trdist.setstatus(node.gateway.spec, "[%d]" % (len(ids)))
        if self.sched.collection_is_completed:
            if self.terminal and not self.sched.has_pending:
                self.trdist.ensure_show_status()
                self.terminal.write_line("")
                if self.config.option.verbose > 0:
                    self.terminal.write_line(
                        "scheduling tests via %s" % (self.sched.__class__.__name__)
                    )
            self.sched.schedule()

    def worker_logstart(self, node, nodeid, location):
        """Emitted when a node calls the pytest_runtest_logstart hook."""
        self.config.hook.pytest_runtest_logstart(nodeid=nodeid, location=location)

    def worker_logfinish(self, node, nodeid, location):
        """Emitted when a node calls the pytest_runtest_logfinish hook."""
        self.config.hook.pytest_runtest_logfinish(nodeid=nodeid, location=location)

    def worker_testreport(self, node, rep):
        """Emitted when a node calls the pytest_runtest_logreport hook."""
        rep.node = node
        self.config.hook.pytest_runtest_logreport(report=rep)
        self._handlefailures(rep)

    def worker_runtest_protocol_complete(self, node, item_index, duration):
        """
        Emitted when a node fires the 'runtest_protocol_complete' event,
        signalling that a test has completed the runtestprotocol and should be
        removed from the pending list in the scheduler.
        """
        self.sched.mark_test_complete(node, item_index, duration)

    def worker_collectreport(self, node, rep):
        """Emitted when a node calls the pytest_collectreport hook.

        Because we only need the report when there's a failure/skip, as optimization
        we only expect to receive failed/skipped reports from workers (#330).
        """
        assert not rep.passed
        self._failed_worker_collectreport(node, rep)

    def worker_warning_captured(self, warning_message, when, item):
        """Emitted when a node calls the pytest_warning_captured hook (deprecated in 6.0)."""
        # This hook as been removed in pytest 7.1, and we can remove support once we only
        # support pytest >=7.1.
        kwargs = dict(warning_message=warning_message, when=when, item=item)
        self.config.hook.pytest_warning_captured.call_historic(kwargs=kwargs)

    def worker_warning_recorded(self, warning_message, when, nodeid, location):
        """Emitted when a node calls the pytest_warning_recorded hook."""
        kwargs = dict(
            warning_message=warning_message, when=when, nodeid=nodeid, location=location
        )
        self.config.hook.pytest_warning_recorded.call_historic(kwargs=kwargs)

    def _clone_node(self, node):
        """Return new node based on an existing one.

        This is normally for when a node dies, this will copy the spec
        of the existing node and create a new one with a new id.  The
        new node will have been setup so it will start calling the
        "worker_*" hooks and do work soon.
        """
        spec = node.gateway.spec
        spec.id = None
        self.nodemanager.group.allocate_id(spec)
        node = self.nodemanager.setup_node(spec, self.queue.put)
        self._active_nodes.add(node)
        return node

    def _failed_worker_collectreport(self, node, rep):
        # Check we haven't already seen this report (from
        # another worker).
        if rep.longrepr not in self._failed_collection_errors:
            self._failed_collection_errors[rep.longrepr] = True
            self.config.hook.pytest_collectreport(report=rep)
            self._handlefailures(rep)

    def _handlefailures(self, rep):
        if rep.failed:
            self.countfailures += 1
            if self.maxfail and self.countfailures >= self.maxfail:
                self.shouldstop = "stopping after %d failures" % (self.countfailures)

    def triggershutdown(self):
        self.log("triggering shutdown")
        self.shuttingdown = True
        for node in self.sched.nodes:
            node.shutdown()

    def handle_crashitem(self, nodeid, worker):
        # XXX get more reporting info by recording pytest_runtest_logstart?
        # XXX count no of failures and retry N times
        runner = self.config.pluginmanager.getplugin("runner")
        fspath = nodeid.split("::")[0]
        msg = f"worker {worker.gateway.id!r} crashed while running {nodeid!r}"
        rep = runner.TestReport(
            nodeid, (fspath, None, fspath), (), "failed", msg, "???"
        )
        rep.node = worker

        self.config.hook.pytest_handlecrashitem(
            crashitem=nodeid,
            report=rep,
            sched=self.sched,
        )
        self.config.hook.pytest_runtest_logreport(report=rep)


class TerminalDistReporter:
    def __init__(self, config):
        self.config = config
        self.tr = config.pluginmanager.getplugin("terminalreporter")
        self._status = {}
        self._lastlen = 0
        self._isatty = getattr(self.tr, "isatty", self.tr.hasmarkup)

    def write_line(self, msg):
        self.tr.write_line(msg)

    def ensure_show_status(self):
        if not self._isatty:
            self.write_line(self.getstatus())

    def setstatus(self, spec, status, show=True):
        self._status[spec.id] = status
        if show and self._isatty:
            self.rewrite(self.getstatus())

    def getstatus(self):
        if self.config.option.verbose >= 0:
            parts = [f"{spec.id} {self._status[spec.id]}" for spec in self._specs]
            return " / ".join(parts)
        else:
            return "bringing up nodes..."

    def rewrite(self, line, newline=False):
        pline = line + " " * max(self._lastlen - len(line), 0)
        if newline:
            self._lastlen = 0
            pline += "\n"
        else:
            self._lastlen = len(line)
        self.tr.rewrite(pline, bold=True)

    @pytest.hookimpl
    def pytest_xdist_setupnodes(self, specs):
        self._specs = specs
        for spec in specs:
            self.setstatus(spec, "I", show=False)
        self.setstatus(spec, "I", show=True)
        self.ensure_show_status()

    @pytest.hookimpl
    def pytest_xdist_newgateway(self, gateway):
        if self.config.option.verbose > 0:
            rinfo = gateway._rinfo()
            version = "%s.%s.%s" % rinfo.version_info[:3]
            self.rewrite(
                "[%s] %s Python %s cwd: %s"
                % (gateway.id, rinfo.platform, version, rinfo.cwd),
                newline=True,
            )
        self.setstatus(gateway.spec, "C")

    @pytest.hookimpl
    def pytest_testnodeready(self, node):
        if self.config.option.verbose > 0:
            d = node.workerinfo
            infoline = "[{}] Python {}".format(
                d["id"], d["version"].replace("\n", " -- ")
            )
            self.rewrite(infoline, newline=True)
        self.setstatus(node.gateway.spec, "ok")

    @pytest.hookimpl
    def pytest_testnodedown(self, node, error):
        if not error:
            return
        self.write_line(f"[{node.gateway.id}] node down: {error}")


def get_default_max_worker_restart(config):
    """gets the default value of --max-worker-restart option if it is not provided.

    Use a reasonable default to avoid workers from restarting endlessly due to crashing collections (#226).
    """
    result = config.option.maxworkerrestart
    if result is not None:
        result = int(result)
    elif config.option.numprocesses:
        # if --max-worker-restart was not provided, use a reasonable default (#226)
        result = config.option.numprocesses * 4
    return result
