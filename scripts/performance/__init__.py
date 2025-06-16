class BaseBenchmarkSuite:
    """
    Base class for performance test suites. This class is used by
    the performance test runner to gather, setup, and clean up
    performance test cases. This class should be extended
    to create performance test cases that can be run by the test runner.
    """

    def __init__(self):
        self.name = self.__class__.__name__
    def get_test_cases(self, args):
        """
        Returns a list of performance test cases. Each element of the returned
        list is a generator that must generate at least args.num_iterations
        definitions for the test case.
        """
        raise NotImplementedError()

    def begin_iteration(self, case, workspace_path, assets_path, iteration):
        """
        Called before each iteration of benchmarking the specified performance
        test case. This method should handle all necessary resource creation
        and environment setup needed for the test case to execute.
        """
        pass

    def end_iteration(self, case, iteration):
        """
        Called after each iteration of benchmarking the specified performance
        test case. This method should handle all necessary teardown and cleanup
        of all resources creating in begin_iteration.
        """
        pass
