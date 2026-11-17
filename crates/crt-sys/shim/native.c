#include "native.h"
#include <aws/auth/auth.h>
#include <aws/auth/signable.h>
#include <aws/auth/signing.h>
#include <aws/auth/signing_result.h>
#include <aws/common/allocator.h>
#include <aws/common/date_time.h>
#include <aws/common/error.h>
#include <aws/common/log_channel.h>
#include <aws/common/log_formatter.h>
#include <aws/common/log_writer.h>
#include <aws/common/logging.h>
#include <aws/common/mutex.h>
#include <aws/common/string.h>
#include <aws/common/uri.h>
#include <aws/common/xml_parser.h>
#include <aws/http/connection.h>
#include <aws/http/proxy.h>
#include <aws/io/socket.h>
#include <aws/io/stream.h>
#include <aws/io/retry_strategy.h>
#include <aws/s3/s3.h>
#include <stdio.h>
#include <string.h>

bool zaws_platform(double *recommended_gbps) {
    *recommended_gbps = 0;
    const struct aws_s3_platform_info *info = aws_s3_get_current_platform_info();
    if (!info) return false;
    *recommended_gbps = info->max_throughput_gbps;
    return info->has_recommended_configuration;
}

struct zaws_proxy {
    struct aws_uri uri;
    bool uri_initialized;
    /* Borrowed by aws_s3_client_new, which copies them. */
    struct aws_http_proxy_options options;
    struct aws_tls_connection_options tls_options;
};
struct zaws_proxy_options {
    struct aws_byte_cursor url;
    /* HTTPS destinations require CONNECT; HTTP destinations use forwarding. */
    bool destination_tls;
    const struct aws_tls_connection_options *tls_options;
    bool verify_peer;
};
struct zaws_runtime {
    struct aws_allocator *allocator;
    struct aws_uri endpoint;
    struct aws_string *region, *signing_region;
    struct aws_event_loop_group *event_loop;
    struct aws_host_resolver *resolver;
    struct aws_client_bootstrap *bootstrap;
    struct aws_credentials_provider *credentials;
    struct aws_credentials *anonymous;
    aws_simple_completion_callback *credentials_shutdown;
    void *credentials_shutdown_data;
    struct aws_string *user_agent;
    bool request_checksum, response_checksum;
    struct aws_tls_ctx *tls;
    struct aws_tls_connection_options tls_options;
    struct proxy_env_var_settings s3_proxy_env;
    struct zaws_proxy proxy;
    struct aws_signing_config_aws signing;
    struct aws_s3_client *client;
    struct zaws_runtime_snapshot snapshot;
    struct zaws_credentials_snapshot credentials_snapshot;
    bool endpoint_live;
};
struct zaws_runtime *zaws_runtime_allocate(void) {
    struct aws_allocator *allocator = rust_crt_allocator();
    struct zaws_runtime *runtime = aws_mem_calloc(allocator, 1, sizeof(*runtime));
    if (runtime) runtime->allocator = allocator;
    return runtime;
}

/* The port urllib3 gives a proxy URL that names none, or port 0: 443 for an `https` proxy and 80
 * for every other, a scheme-less URL included. The CRT's URI parser leaves such a port 0, which no
 * socket connects to. */
static uint32_t s_default_proxy_port(bool proxy_tls) {
    return proxy_tls ? 443 : 80;
}
static void s_proxy_clean_up(struct zaws_proxy *p) {
    aws_http_proxy_strategy_release(p->options.proxy_strategy);
    aws_tls_connection_options_clean_up(&p->tls_options);
    if (p->uri_initialized) aws_uri_clean_up(&p->uri);
    AWS_ZERO_STRUCT(*p);
}
static int s_proxy_init_tls(struct zaws_proxy *p, struct aws_allocator *allocator, const struct zaws_proxy_options *o) {
    if (o->tls_options) {
        if (aws_tls_connection_options_copy(&p->tls_options, o->tls_options)) return AWS_OP_ERR;
    } else {
        struct aws_tls_ctx_options options;
        aws_tls_ctx_options_init_default_client(&options, allocator);
        aws_tls_ctx_options_set_verify_peer(&options, o->verify_peer);
        struct aws_tls_ctx *ctx = aws_tls_client_ctx_new(allocator, &options);
        aws_tls_ctx_options_clean_up(&options);
        if (!ctx) return AWS_OP_ERR;
        aws_tls_connection_options_init_from_ctx(&p->tls_options, ctx);
        aws_tls_ctx_release(ctx);
    }
    return aws_tls_connection_options_set_server_name(&p->tls_options, allocator, &p->uri.host_name);
}
static int s_proxy_init(struct zaws_proxy *p, struct aws_allocator *allocator, const struct zaws_proxy_options *o) {
    AWS_ZERO_STRUCT(*p);
    if (!o->url.len) return AWS_OP_SUCCESS;
    if (aws_uri_init_parse(&p->uri, allocator, &o->url)) return AWS_OP_ERR;
    p->uri_initialized = true;
    /* A URL without `scheme://` leaves the scheme cursor empty. */
    bool proxy_tls = aws_byte_cursor_eq_c_str_ignore_case(&p->uri.scheme, "https");
    p->options.host = p->uri.host_name;
    p->options.port = p->uri.port ? p->uri.port : s_default_proxy_port(proxy_tls);
    p->options.connection_type = o->destination_tls ? AWS_HPCT_HTTP_TUNNEL : AWS_HPCT_HTTP_FORWARD;
    if (proxy_tls) {
        if (s_proxy_init_tls(p, allocator, o)) goto fail;
        p->options.tls_options = &p->tls_options;
    }
    if (p->uri.password.len) {
        struct aws_http_proxy_strategy_basic_auth_options auth = {
            .proxy_connection_type = p->options.connection_type,
            .user_name = p->uri.user, .password = p->uri.password,
        };
        p->options.proxy_strategy = aws_http_proxy_strategy_new_basic_auth(allocator, &auth);
        if (!p->options.proxy_strategy) goto fail;
    }
    return AWS_OP_SUCCESS;
fail:
    s_proxy_clean_up(p);
    return AWS_OP_ERR;
}
static const struct aws_http_proxy_options *s_proxy_connection_options(const struct zaws_proxy *p) {
    return p->uri_initialized ? &p->options : NULL;
}

static int s_initialize_endpoint(struct zaws_runtime *r, const struct zaws_runtime_options *o) {
    if (!o->endpoint.len || aws_uri_init_parse(&r->endpoint, r->allocator, &o->endpoint)) return AWS_OP_ERR;
    r->endpoint_live = true;
    if (!r->endpoint.authority.len || r->endpoint.query_string.len) return aws_raise_error(AWS_ERROR_INVALID_ARGUMENT);
    return AWS_OP_SUCCESS;
}
static void s_release_endpoint(struct zaws_runtime *r) {
    if (r->endpoint_live) { aws_uri_clean_up(&r->endpoint); r->endpoint_live = false; }
}
static int s_allocate_region(struct zaws_runtime *r, const struct zaws_runtime_options *o) {
    r->region = aws_string_new_from_cursor(r->allocator, &o->region);
    r->signing_region = aws_string_new_from_cursor(r->allocator, &o->signing_region);
    r->user_agent = aws_string_new_from_cursor(r->allocator, &o->user_agent);
    r->request_checksum = o->request_checksum;
    r->response_checksum = o->response_checksum;
    return r->region && r->signing_region && r->user_agent ? AWS_OP_SUCCESS : AWS_OP_ERR;
}
static void s_free_region(struct zaws_runtime *r) {
    aws_string_destroy(r->user_agent); r->user_agent = NULL;
    aws_string_destroy(r->signing_region); r->signing_region = NULL;
    aws_string_destroy(r->region); r->region = NULL;
}
static int s_create_event_loop(struct zaws_runtime *r, const struct zaws_runtime_options *o, aws_simple_completion_callback *cb, void *data) {
    r->event_loop = rust_crt_event_loop_new(r->allocator, o->event_loop_count, cb, data);
    return r->event_loop ? AWS_OP_SUCCESS : AWS_OP_ERR;
}
static void s_release_event_loop(struct zaws_runtime *r) {
    aws_event_loop_group_release(r->event_loop); r->event_loop = NULL;
}
static int s_create_resolver(struct zaws_runtime *r, aws_simple_completion_callback *cb, void *data) {
    r->resolver = rust_crt_resolver_new(r->allocator, r->event_loop, cb, data);
    return r->resolver ? AWS_OP_SUCCESS : AWS_OP_ERR;
}
static void s_release_resolver(struct zaws_runtime *r) {
    aws_host_resolver_release(r->resolver); r->resolver = NULL;
}
static int s_create_bootstrap(struct zaws_runtime *r, aws_simple_completion_callback *cb, void *data) {
    r->bootstrap = rust_crt_bootstrap_new(r->allocator, r->event_loop, r->resolver, cb, data);
    return r->bootstrap ? AWS_OP_SUCCESS : AWS_OP_ERR;
}
static void s_release_bootstrap(struct zaws_runtime *r) {
    aws_client_bootstrap_release(r->bootstrap); r->bootstrap = NULL;
}
static int s_configure_tls(struct aws_tls_ctx_options *options, const struct zaws_runtime_options *o) {
    aws_tls_ctx_options_set_verify_peer(options, o->verify_peer);
    if (o->ca_bundle) {
        if (aws_tls_ctx_options_override_default_trust_store_from_path(options, NULL, o->ca_bundle)) return ZAWS_TRUST_FILE_REJECTED;
    } else if (o->ca_pem.len) {
        return aws_tls_ctx_options_override_default_trust_store(options, &o->ca_pem);
    }
    return AWS_OP_SUCCESS;
}
static int s_create_tls_context(struct zaws_runtime *r, const struct zaws_runtime_options *o) {
    struct aws_tls_ctx_options options;
    aws_tls_ctx_options_init_default_client(&options, r->allocator);
    int rc = s_configure_tls(&options, o);
    if (!rc) r->tls = aws_tls_client_ctx_new(r->allocator, &options);
    aws_tls_ctx_options_clean_up(&options);
    if (rc) return rc;
    if (!r->tls) return AWS_OP_ERR;
    aws_tls_connection_options_init_from_ctx(&r->tls_options, r->tls);
    return AWS_OP_SUCCESS;
}
static void s_release_tls_context(struct zaws_runtime *r) {
    aws_tls_connection_options_clean_up(&r->tls_options);
    aws_tls_ctx_release(r->tls); r->tls = NULL;
}
static int s_create_credentials(struct zaws_runtime *r, const struct zaws_runtime_options *o, aws_simple_completion_callback *cb, void *data) {
    r->credentials_shutdown = cb;
    r->credentials_shutdown_data = data;
    if (o->no_sign_request) {
        r->anonymous = aws_credentials_new_anonymous(r->allocator);
        return r->anonymous ? AWS_OP_SUCCESS : AWS_OP_ERR;
    }
    if (!o->credentials_delegate) return aws_raise_error(AWS_ERROR_INVALID_ARGUMENT);
    struct aws_credentials_provider_delegate_options delegate = {
        .shutdown_options = { .shutdown_callback = cb, .shutdown_user_data = data },
        .get_credentials = o->credentials_delegate, .delegate_user_data = o->credentials_delegate_data,
    };
    r->credentials_snapshot = (struct zaws_credentials_snapshot) { .delegate = true };
    r->credentials = aws_credentials_provider_new_delegate(r->allocator, &delegate);
    return r->credentials ? AWS_OP_SUCCESS : AWS_OP_ERR;
}
void zaws_credentials_complete(aws_on_get_credentials_callback_fn *callback, void *callback_data, const struct zaws_credentials_view *view) {
    struct aws_credentials *credentials = NULL;
    int error = AWS_AUTH_CREDENTIALS_PROVIDER_DELEGATE_FAILURE;
    if (view) {
        struct aws_credentials_options options = {
            .access_key_id_cursor = view->access_key_id, .secret_access_key_cursor = view->secret_access_key,
            .session_token_cursor = view->session_token, .account_id_cursor = view->account_id,
            .expiration_timepoint_seconds = view->expiration_timepoint_seconds,
        };
        credentials = aws_credentials_new_with_options(rust_crt_allocator(), &options);
        if (!credentials) error = aws_last_error();
    }
    /* The callback takes its own reference. */
    callback(credentials, credentials ? AWS_ERROR_SUCCESS : error, callback_data);
    aws_credentials_release(credentials);
}
static void s_release_credentials(struct zaws_runtime *r) {
    if (r->anonymous) {
        aws_credentials_release(r->anonymous); r->anonymous = NULL;
        r->credentials_shutdown(r->credentials_shutdown_data);
        return;
    }
    aws_credentials_provider_release(r->credentials); r->credentials = NULL;
}
static int s_create_client_proxy(struct zaws_runtime *r, const struct zaws_runtime_options *o, bool destination_tls) {
    struct zaws_proxy_options options = {
        .url = o->proxy_url, .destination_tls = destination_tls,
        .tls_options = r->tls ? &r->tls_options : NULL, .verify_peer = o->verify_peer,
    };
    return s_proxy_init(&r->proxy, r->allocator, &options);
}
static void s_configure_signing(struct zaws_runtime *r) {
    if (r->anonymous) {
        r->signing.config_type = AWS_SIGNING_CONFIG_AWS;
        r->signing.algorithm = AWS_SIGNING_ALGORITHM_V4;
        r->signing.region = aws_byte_cursor_from_string(r->signing_region);
        r->signing.service = aws_byte_cursor_from_c_str("s3");
        r->signing.signed_body_header = AWS_SBHT_X_AMZ_CONTENT_SHA256;
        r->signing.signed_body_value = aws_byte_cursor_from_c_str("UNSIGNED-PAYLOAD");
        r->signing.credentials = r->anonymous;
    } else {
        aws_s3_init_default_signing_config(&r->signing, aws_byte_cursor_from_string(r->signing_region), r->credentials);
    }
}
static int s_create_retry_strategy(struct zaws_runtime *r, const struct zaws_runtime_options *o, struct aws_retry_strategy **out) {
    *out = NULL;
    if (!o->max_attempts) return AWS_OP_SUCCESS;
    struct aws_standard_retry_options retry = {0};
    retry.backoff_retry_options.el_group = r->event_loop;
    retry.backoff_retry_options.max_retries = o->max_attempts - 1;
    *out = aws_retry_strategy_new_standard(r->allocator, &retry);
    return *out ? AWS_OP_SUCCESS : AWS_OP_ERR;
}
/* Storage s_configure_client_options points the client config into, which must outlive
 * aws_s3_client_new; the client copies both. */
struct client_config_storage {
    /* Zeroed: SO_KEEPALIVE with the system's timings. */
    struct aws_s3_tcp_keep_alive_options keep_alive;
    struct aws_s3_file_io_options file_io;
};
static void s_configure_client_options(struct aws_s3_client_config *config, struct client_config_storage *storage, const struct zaws_runtime_options *o, struct aws_retry_strategy *retry_strategy) {
    config->retry_strategy = retry_strategy;
    config->throughput_target_gbps = o->throughput_target_gbps > 0 ? o->throughput_target_gbps : 10.0;
    config->memory_limit_in_bytes = o->memory_limit;
    config->connect_timeout_ms = o->connect_timeout_ms;
    config->tcp_keep_alive_options = o->keep_alive ? &storage->keep_alive : NULL;
    config->part_size = o->part_size;
    config->multipart_upload_threshold = o->multipart_upload_threshold;
    config->max_active_connections_override = o->max_connections;
    if (o->has_file_io) {
        storage->file_io = (struct aws_s3_file_io_options) { .should_stream = o->file_should_stream,
            .disk_throughput_gbps = o->disk_throughput_gbps, .direct_io = o->file_direct_io };
        config->fio_opts = &storage->file_io;
    }
    config->buffer_pool_factory_fn = o->pool_factory;
    config->buffer_pool_user_data = o->pool_data;
}
static void s_record_client_snapshot(struct zaws_runtime *r, const struct aws_s3_client_config *config, const struct zaws_runtime_options *o) {
    const struct aws_s3_file_io_options none = {0};
    const struct aws_s3_file_io_options *fio = config->fio_opts ? config->fio_opts : &none;
    r->snapshot = (struct zaws_runtime_snapshot) {
        .part_size = config->part_size, .max_part_size = config->max_part_size,
        .multipart_threshold = config->multipart_upload_threshold, .memory_limit = config->memory_limit_in_bytes,
        .throughput_gbps = config->throughput_target_gbps,
        .disk_gbps = fio->disk_throughput_gbps, .max_connections = config->max_active_connections_override,
        .connect_timeout_ms = config->connect_timeout_ms, .max_retries = o->max_attempts ? o->max_attempts - 1 : 0,
        .anonymous = r->anonymous != NULL, .shared_tls = config->tls_connection_options == &r->tls_options && r->tls != NULL,
        .verify_peer = r->tls_options.ctx != NULL && o->verify_peer, .keep_alive = config->tcp_keep_alive_options != NULL,
        .file_io = config->fio_opts != NULL, .stream = fio->should_stream, .direct = fio->direct_io,
        .request_checksum = r->request_checksum, .response_checksum = r->response_checksum,
    };
}
static int s_create_client(struct zaws_runtime *r, const struct zaws_runtime_options *o, aws_simple_completion_callback *cb, void *data) {
    bool tls = aws_byte_cursor_eq_c_str_ignore_case(&r->endpoint.scheme, "https");
    if (!tls && !aws_byte_cursor_eq_c_str_ignore_case(&r->endpoint.scheme, "http")) return aws_raise_error(AWS_ERROR_INVALID_ARGUMENT);
    if (s_create_client_proxy(r, o, tls)) return AWS_OP_ERR;
    s_configure_signing(r);
    struct aws_retry_strategy *retry_strategy = NULL;
    if (s_create_retry_strategy(r, o, &retry_strategy)) {
        s_proxy_clean_up(&r->proxy);
        return ZAWS_CLIENT_FAILED_WITH_PROXY;
    }
    struct aws_s3_client_config config = {0};
    struct client_config_storage storage = {0};
    s_configure_client_options(&config, &storage, o, retry_strategy);
    config.region = aws_byte_cursor_from_string(r->region);
    config.client_bootstrap = r->bootstrap;
    config.tls_mode = tls ? AWS_MR_TLS_ENABLED : AWS_MR_TLS_DISABLED;
    /* Without these aws-c-s3 builds its own default-trust-store context. */
    config.tls_connection_options = r->tls ? &r->tls_options : NULL;
    r->s3_proxy_env.env_var_type = AWS_HPEV_DISABLE;
    r->s3_proxy_env.connection_type = AWS_HPCT_HTTP_LEGACY;
    config.proxy_ev_settings = &r->s3_proxy_env;
    config.proxy_options = s_proxy_connection_options(&r->proxy);
    config.signing_config = &r->signing;
    config.shutdown_callback = cb;
    config.shutdown_callback_user_data = data;
    s_record_client_snapshot(r, &config, o);
    r->client = aws_s3_client_new(r->allocator, &config);
    int error = aws_last_error();
    aws_retry_strategy_release(retry_strategy);
    if (r->client) return AWS_OP_SUCCESS;
    s_proxy_clean_up(&r->proxy);
    aws_raise_error(error);
    return ZAWS_CLIENT_FAILED_WITH_PROXY;
}
static void s_release_client(struct zaws_runtime *r) {
    aws_s3_client_release(r->client); r->client = NULL;
    s_proxy_clean_up(&r->proxy);
}
/* One zaws_http_request, from signing to the connection's shutdown. The caller and the CRT each
 * hold a reference. `lock` guards `connection` and `cancelled`, which zaws_http_cancel reads on
 * the caller's thread while the CRT's threads write them. */
struct zaws_http_call {
    struct aws_atomic_var refs;
    struct aws_allocator *allocator;
    /* Live until `finish`: the runtime's bootstrap stage waits for the connection's shutdown. */
    struct zaws_runtime *runtime;
    struct aws_http_message *message;
    struct aws_signable *signable;
    struct aws_string *host;
    uint32_t port, connect_timeout_ms;
    /* For a call over TLS: the runtime's connection options with this call's server name and
     * negotiation timeout, copied while the caller holds the runtime's TLS stage in place. */
    bool tls;
    struct aws_tls_connection_options tls_options;
    /* Why the handshake failed, written and read on the connection's thread. */
    int handshake_error;
    struct aws_mutex lock;
    /* The reference `s_http_on_setup` received, until the stream completes or fails to start. */
    struct aws_http_connection *connection;
    bool cancelled;
    zaws_http_event_fn *event;
    zaws_http_finish_fn *finish;
    void *data;
    int error, status;
};
void zaws_http_release(struct zaws_http_call *call) {
    if (!call || aws_atomic_fetch_sub(&call->refs, 1) != 1) return;
    aws_signable_destroy(call->signable);
    aws_http_message_release(call->message);
    aws_string_destroy(call->host);
    if (call->tls) aws_tls_connection_options_clean_up(&call->tls_options);
    aws_mutex_clean_up(&call->lock);
    aws_mem_release(call->allocator, call);
}
static void s_http_call_finish(struct zaws_http_call *call) {
    call->finish(call->error, call->status, call->data);
    zaws_http_release(call);
}
/* Gives up the connection's reference, once. Its shutdown follows and finishes the call. */
static void s_http_release_connection(struct zaws_http_call *call) {
    aws_mutex_lock(&call->lock);
    struct aws_http_connection *connection = call->connection;
    call->connection = NULL;
    aws_mutex_unlock(&call->lock);
    aws_http_connection_release(connection);
}
void zaws_http_cancel(struct zaws_http_call *call) {
    aws_mutex_lock(&call->lock);
    call->cancelled = true;
    /* Safe from any thread while the reference is held, which the lock ensures. */
    if (call->connection) aws_http_connection_close(call->connection);
    aws_mutex_unlock(&call->lock);
}
/* Runs once the connection a successful setup returned has shut down. */
static void s_http_on_shutdown(struct aws_http_connection *connection, int error, void *data) {
    (void)connection; (void)error;
    s_http_call_finish(data);
}
static int s_http_on_headers(struct aws_http_stream *stream, enum aws_http_header_block block, const struct aws_http_header *headers, size_t count, void *data) {
    (void)stream; (void)block; (void)headers; (void)count;
    struct zaws_http_call *call = data;
    call->event(ZAWS_HTTP_HEADERS, (struct aws_byte_cursor){0}, call->data);
    return AWS_OP_SUCCESS;
}
static int s_http_on_body(struct aws_http_stream *stream, const struct aws_byte_cursor *body, void *data) {
    (void)stream;
    struct zaws_http_call *call = data;
    call->event(ZAWS_HTTP_BODY, *body, call->data);
    return AWS_OP_SUCCESS;
}
static void s_http_on_stream_complete(struct aws_http_stream *stream, int error, void *data) {
    struct zaws_http_call *call = data;
    call->error = error;
    if (!error && aws_http_stream_get_incoming_response_status(stream, &call->status)) call->error = aws_last_error();
    aws_http_stream_release(stream);
    s_http_release_connection(call);
}
static void s_http_on_setup(struct aws_http_connection *connection, int error, void *data) {
    struct zaws_http_call *call = data;
    if (!connection) {
        call->error = call->handshake_error ? call->handshake_error : error;
        s_http_call_finish(call);
        return;
    }
    aws_mutex_lock(&call->lock);
    call->connection = connection;
    bool cancelled = call->cancelled;
    aws_mutex_unlock(&call->lock);
    if (cancelled) {
        call->error = AWS_ERROR_HTTP_STREAM_CANCELLED;
        s_http_release_connection(call);
        return;
    }
    struct aws_http_make_request_options options = {
        .self_size = sizeof(options), .request = call->message, .user_data = call,
        .on_response_headers = s_http_on_headers, .on_response_body = s_http_on_body,
        .on_complete = s_http_on_stream_complete,
    };
    struct aws_http_stream *stream = aws_http_connection_make_request(connection, &options);
    if (!stream || aws_http_stream_activate(stream)) {
        /* aws-c-http refused the request itself, a header value it will not send among others. */
        call->error = aws_last_error();
        aws_http_stream_release(stream);
        s_http_release_connection(call);
        return;
    }
    /* Reported on this connection's own thread, so before anything of the response. */
    call->event(ZAWS_HTTP_CONNECTED, (struct aws_byte_cursor){0}, call->data);
}
/* Connects on the runtime's bootstrap, in plaintext or with the call's TLS options. The
 * environment's proxies are never read: a caller with a proxy connects to it and sends an
 * absolute target. */
static int s_http_connect(struct zaws_http_call *call) {
    struct aws_socket_options socket = { .type = AWS_SOCKET_STREAM, .domain = AWS_SOCKET_IPV4, .connect_timeout_ms = call->connect_timeout_ms };
    struct proxy_env_var_settings proxy = { .env_var_type = AWS_HPEV_DISABLE };
    struct aws_http_client_connection_options options = AWS_HTTP_CLIENT_CONNECTION_OPTIONS_INIT;
    options.allocator = call->allocator;
    options.bootstrap = call->runtime->bootstrap;
    options.host_name = aws_byte_cursor_from_string(call->host);
    options.port = call->port;
    options.socket_options = &socket;
    options.tls_options = call->tls ? &call->tls_options : NULL;
    options.proxy_ev_settings = &proxy;
    options.user_data = call;
    options.on_setup = s_http_on_setup;
    options.on_shutdown = s_http_on_shutdown;
    return aws_http_client_connect(&options);
}
/* Runs on the thread that answered the credentials query: the caller's for an answer during the
 * delegate's call, else the delegate's own. */
static void s_http_on_signed(struct aws_signing_result *result, int error, void *data) {
    struct zaws_http_call *call = data;
    if (error || aws_apply_signing_result_to_http_request(call->message, call->allocator, result) || s_http_connect(call)) {
        call->error = error ? error : aws_last_error();
        s_http_call_finish(call);
    }
}
/* Runs on the connection's thread as the handshake ends, before the bootstrap shuts a failed
 * channel down with the failure's code. s2n's handler then holds the channel open for s2n's
 * blinding delay, ten to thirty seconds, unless the shutdown's code is AWS_IO_SOCKET_CLOSED
 * (aws-c-io's s2n channel handler). The CRT reports the failed setup only
 * after that, and the runtime's bootstrap stage waits for the channel, so neither this call's
 * timeout nor the runtime's release would bound a certificate that does not verify. A channel
 * takes its first shutdown's code, so this shuts it down first, with the code that is not
 * delayed, and keeps the failure's own for `finish`.
 *
 * What is given up is the delay's cover for how long this client took to fail a handshake. It
 * has no certificate of its own, and a handshake that failed carried no request. */
static void s_http_on_negotiated(struct aws_channel_handler *handler, struct aws_channel_slot *slot, int error, void *data) {
    (void)handler;
    struct zaws_http_call *call = data;
    if (!error) return;
    call->handshake_error = error;
    aws_channel_shutdown(slot->channel, AWS_IO_SOCKET_CLOSED);
}
/* The runtime's trust and peer verification, for a server named as the call's host. The CRT's
 * handshake timer (`timeout_ms`, ten seconds when it is zero) gets the connect's own bound: a
 * handshake, like a connect, has no handle to cancel it by. */
static int s_http_init_tls(struct zaws_http_call *call) {
    struct zaws_runtime *r = call->runtime;
    if (!r->tls) return aws_raise_error(AWS_ERROR_INVALID_STATE);
    if (aws_tls_connection_options_copy(&call->tls_options, &r->tls_options)) return AWS_OP_ERR;
    call->tls = true;
    call->tls_options.timeout_ms = call->connect_timeout_ms;
    call->tls_options.on_negotiation_result = s_http_on_negotiated;
    call->tls_options.user_data = call;
    struct aws_byte_cursor host = aws_byte_cursor_from_string(call->host);
    return aws_tls_connection_options_set_server_name(&call->tls_options, call->allocator, &host);
}
static int s_http_init_message(struct zaws_http_call *call, const struct zaws_http_options *o) {
    call->host = aws_string_new_from_cursor(call->allocator, &o->host);
    call->message = aws_http_message_new_request(call->allocator);
    if (!call->host || !call->message) return AWS_OP_ERR;
    if (aws_http_message_set_request_method(call->message, o->method) || aws_http_message_set_request_path(call->message, o->target)) return AWS_OP_ERR;
    for (size_t i = 0; i < o->header_count; i++) {
        struct aws_http_header header = { .name = o->headers[i].name, .value = o->headers[i].value };
        if (aws_http_message_add_header(call->message, header)) return AWS_OP_ERR;
    }
    return AWS_OP_SUCCESS;
}
/* Signs the request with SigV4 for `service` in `region`, through the provider the runtime's
 * credentials stage built or with its anonymous credentials, then connects. The signer copies the
 * region and the service before it returns. */
static int s_http_sign(struct zaws_http_call *call, const struct zaws_http_options *o) {
    struct zaws_runtime *r = call->runtime;
    call->signable = aws_signable_new_http_request(call->allocator, call->message);
    if (!call->signable) return AWS_OP_ERR;
    struct aws_signing_config_aws config = {
        .config_type = AWS_SIGNING_CONFIG_AWS, .algorithm = AWS_SIGNING_ALGORITHM_V4,
        .signature_type = AWS_ST_HTTP_REQUEST_HEADERS, .region = o->region, .service = o->service,
        .signed_body_header = AWS_SBHT_X_AMZ_CONTENT_SHA256,
        .credentials = r->anonymous, .credentials_provider = r->credentials,
    };
    aws_date_time_init_now(&config.date);
    return aws_sign_request_aws(call->allocator, call->signable, (struct aws_signing_config_base *)&config, s_http_on_signed, call);
}
struct zaws_http_call *zaws_http_request(struct zaws_runtime *r, const struct zaws_http_options *o, zaws_http_event_fn *event, zaws_http_finish_fn *finish, void *data) {
    struct aws_allocator *allocator = rust_crt_allocator();
    struct zaws_http_call *call = aws_mem_calloc(allocator, 1, sizeof(*call));
    if (!call) return NULL;
    /* One reference is the caller's and one the CRT's, which `finish` gives up. */
    aws_atomic_init_int(&call->refs, 2);
    call->allocator = allocator; call->runtime = r;
    call->event = event; call->finish = finish; call->data = data;
    call->port = o->port; call->connect_timeout_ms = o->connect_timeout_ms;
    if (aws_mutex_init(&call->lock)) { aws_mem_release(allocator, call); return NULL; }
    if (s_http_init_message(call, o)) goto fail;
    if (o->tls && s_http_init_tls(call)) goto fail;
    if (o->service.len ? s_http_sign(call, o) : s_http_connect(call)) goto fail;
    return call;
fail:
    /* Nothing started, so no callback holds the second reference. */
    aws_atomic_store_int(&call->refs, 1);
    zaws_http_release(call);
    return NULL;
}
int zaws_runtime_start_stage(struct zaws_runtime *r, enum zaws_runtime_stage stage, const struct zaws_runtime_options *o, aws_simple_completion_callback *cb, void *data) {
    switch (stage) {
    case ZAWS_STAGE_ENDPOINT: return s_initialize_endpoint(r, o);
    case ZAWS_STAGE_REGION: return s_allocate_region(r, o);
    case ZAWS_STAGE_EVENT_LOOP: return s_create_event_loop(r, o, cb, data);
    case ZAWS_STAGE_RESOLVER: return s_create_resolver(r, cb, data);
    case ZAWS_STAGE_BOOTSTRAP: return s_create_bootstrap(r, cb, data);
    case ZAWS_STAGE_TLS: return s_create_tls_context(r, o);
    case ZAWS_STAGE_CREDENTIALS: return s_create_credentials(r, o, cb, data);
    case ZAWS_STAGE_CLIENT: return s_create_client(r, o, cb, data);
    }
    return aws_raise_error(AWS_ERROR_INVALID_ARGUMENT);
}
void zaws_runtime_release_stage(struct zaws_runtime *r, enum zaws_runtime_stage stage) {
    switch (stage) {
    case ZAWS_STAGE_CLIENT: s_release_client(r); break;
    case ZAWS_STAGE_CREDENTIALS: s_release_credentials(r); break;
    case ZAWS_STAGE_TLS: s_release_tls_context(r); break;
    case ZAWS_STAGE_BOOTSTRAP: s_release_bootstrap(r); break;
    case ZAWS_STAGE_RESOLVER: s_release_resolver(r); break;
    case ZAWS_STAGE_EVENT_LOOP: s_release_event_loop(r); break;
    case ZAWS_STAGE_REGION: s_free_region(r); break;
    case ZAWS_STAGE_ENDPOINT: s_release_endpoint(r); break;
    }
}
void zaws_runtime_destroy(struct zaws_runtime *r) { aws_mem_release(r->allocator, r); }
void zaws_runtime_snapshot(struct zaws_runtime *r, struct zaws_runtime_snapshot *out) { *out = r->snapshot; }
void zaws_credentials_snapshot(struct zaws_runtime *r, struct zaws_credentials_snapshot *out) { *out = r->credentials_snapshot; }
void zaws_runtime_signing_snapshot(struct zaws_runtime *r, struct zaws_signing_snapshot *out) {
    *out = (struct zaws_signing_snapshot) {
        .region = r->signing.region, .service = r->signing.service, .body = r->signing.signed_body_value,
        .validation = aws_validate_aws_signing_config_aws(&r->signing),
        .chain = r->credentials != NULL, .provider = r->signing.credentials_provider != NULL,
        .anonymous = r->anonymous != NULL && aws_credentials_is_anonymous(r->anonymous),
        .same_credentials = r->anonymous != NULL && r->signing.credentials == r->anonymous,
    };
}

struct aws_http_message *zaws_message_new(struct aws_byte_cursor host, struct aws_byte_cursor path, struct aws_byte_cursor method, const uint64_t *length, struct aws_byte_cursor content_type, bool conditional, struct aws_byte_cursor if_match, struct aws_byte_cursor request_payer, const struct zaws_header *extra, size_t extra_count, struct aws_byte_cursor user_agent) {
    struct aws_http_message *message = aws_http_message_new_request(rust_crt_allocator());
    if (!message) return NULL;
    struct aws_http_header headers[8] = {
        {.name = AWS_BYTE_CUR_INIT_FROM_STRING_LITERAL("Host"), .value = host},
        {.name = AWS_BYTE_CUR_INIT_FROM_STRING_LITERAL("accept"), .value = AWS_BYTE_CUR_INIT_FROM_STRING_LITERAL("*/*")},
    };
    size_t count = 2;
    char length_text[21];
    if (length) {
        snprintf(length_text, sizeof(length_text), "%llu", (unsigned long long)*length);
        headers[count++] = (struct aws_http_header){ .name = AWS_BYTE_CUR_INIT_FROM_STRING_LITERAL("content-length"), .value = aws_byte_cursor_from_c_str(length_text) };
    }
    if (content_type.len) headers[count++] = (struct aws_http_header){ .name = AWS_BYTE_CUR_INIT_FROM_STRING_LITERAL("Content-Type"), .value = content_type };
    if (conditional) headers[count++] = (struct aws_http_header){ .name = AWS_BYTE_CUR_INIT_FROM_STRING_LITERAL("If-None-Match"), .value = AWS_BYTE_CUR_INIT_FROM_STRING_LITERAL("*") };
    if (if_match.len) headers[count++] = (struct aws_http_header){ .name = AWS_BYTE_CUR_INIT_FROM_STRING_LITERAL("If-Match"), .value = if_match };
    if (request_payer.len) headers[count++] = (struct aws_http_header){ .name = AWS_BYTE_CUR_INIT_FROM_STRING_LITERAL("x-amz-request-payer"), .value = request_payer };
    for (size_t i = 0; i < count; i++) if (aws_http_message_add_header(message, headers[i])) goto fail;
    for (size_t i = 0; i < extra_count; i++) {
        struct aws_http_header header = { .name = extra[i].name, .value = extra[i].value };
        if (aws_http_message_add_header(message, header)) goto fail;
    }
    struct aws_http_header agent = { .name = AWS_BYTE_CUR_INIT_FROM_STRING_LITERAL("user-agent"), .value = user_agent };
    if (aws_http_message_add_header(message, agent)) goto fail;
    if (aws_http_message_set_request_method(message, method) || aws_http_message_set_request_path(message, path)) goto fail;
    return message;
fail: aws_http_message_release(message); return NULL;
}
int zaws_message_field(const struct aws_http_message *m, unsigned index, struct aws_byte_cursor *name, struct aws_byte_cursor *value) {
    if (index == 0) return aws_http_message_get_request_method(m, value);
    if (index == 1) return aws_http_message_get_request_path(m, value);
    struct aws_http_header h;
    int rc = aws_http_message_get_header(m, &h, index - 2);
    if (!rc) { *name = h.name; *value = h.value; }
    return rc;
}
int zaws_parse_http_date(struct aws_byte_cursor value, int64_t *out) {
    struct aws_date_time date;
    if (!value.len || aws_date_time_init_from_str_cursor(&date, &value, AWS_DATE_FORMAT_RFC822)) return AWS_OP_ERR;
    *out = date.timestamp; return AWS_OP_SUCCESS;
}
int zaws_parse_date(struct aws_byte_cursor value, struct zaws_date *out) {
    struct aws_date_time date;
    if (aws_date_time_init_from_str_cursor(&date, &value, AWS_DATE_FORMAT_AUTO_DETECT)) return AWS_OP_ERR;
    out->fields[0] = aws_date_time_year(&date, true);
    out->fields[1] = aws_date_time_month(&date, true) + 1;
    out->fields[2] = aws_date_time_month_day(&date, true);
    out->fields[3] = aws_date_time_hour(&date, true);
    out->fields[4] = aws_date_time_minute(&date, true);
    out->fields[5] = aws_date_time_second(&date, true);
    out->epoch_seconds = date.timestamp;
    return AWS_OP_SUCCESS;
}
int zaws_xml_parse(struct aws_byte_cursor body, aws_xml_parser_on_node_encountered_fn *root, void *data) {
    struct aws_xml_parser_options options = { .doc = body, .max_depth = 16, .on_root_encountered = root, .user_data = data };
    return aws_xml_parse(rust_crt_allocator(), &options);
}
int zaws_xml_unescape(struct aws_byte_cursor text, uint8_t *out, size_t *out_len) {
    struct aws_byte_buf decoded;
    if (aws_byte_buf_init(&decoded, rust_crt_allocator(), text.len)) return AWS_OP_ERR;
    int rc = aws_byte_buf_append_unescaped_xml(rust_crt_allocator(), text, &decoded);
    if (!rc && decoded.len > text.len) rc = aws_raise_error(AWS_ERROR_INVALID_STATE);
    if (!rc) {
        if (decoded.len) memcpy(out, decoded.buffer, decoded.len);
        *out_len = decoded.len;
    }
    aws_byte_buf_clean_up(&decoded);
    return rc;
}
int zaws_listing_error(unsigned kind) {
    switch (kind) {
        case 0: return AWS_ERROR_INVALID_XML;
        case 1: return AWS_ERROR_MALFORMED_INPUT_STRING;
        case 2: return AWS_ERROR_S3_EXCEEDS_MEMORY_LIMIT;
        default: return AWS_ERROR_INVALID_ARGUMENT;
    }
}

struct request_state {
    struct aws_allocator *allocator;
    struct aws_http_message *message;
    zaws_headers_fn *headers;
    zaws_body_fn *body;
    zaws_finish_fn *finish;
    zaws_progress_fn *progress;
    struct aws_s3_checksum_config checksum;
    zaws_telemetry_fn *telemetry;
    aws_simple_completion_callback *shutdown;
    void *data;
};
static void s_request_free(struct request_state *r) {
    aws_http_message_release(r->message);
    aws_mem_release(r->allocator, r);
}
static bool s_region_header(const struct aws_http_headers *h, struct aws_byte_cursor *value) {
    return h && aws_http_headers_get(h, aws_byte_cursor_from_c_str("x-amz-bucket-region"), value) == AWS_OP_SUCCESS;
}
/* Whether any checksum header botocore parses into a HeadObject's checksum members has a value
 * (s3transfer/constants.py `FULL_OBJECT_CHECKSUM_ARGS`). */
static bool s_checksum_reported(const struct aws_http_headers *h) {
    static const char *names[] = {
        "x-amz-checksum-crc32", "x-amz-checksum-crc32c", "x-amz-checksum-crc64nvme", "x-amz-checksum-md5",
        "x-amz-checksum-sha1", "x-amz-checksum-sha256", "x-amz-checksum-sha512", "x-amz-checksum-xxhash3",
        "x-amz-checksum-xxhash64", "x-amz-checksum-xxhash128",
    };
    for (size_t i = 0; i < AWS_ARRAY_SIZE(names); i++) {
        struct aws_byte_cursor value = {0};
        if (aws_http_headers_get(h, aws_byte_cursor_from_c_str(names[i]), &value) == AWS_OP_SUCCESS && value.len) return true;
    }
    return false;
}
static int s_headers(struct aws_s3_meta_request *m, const struct aws_http_headers *h, int status, void *data) {
    (void)m;
    struct request_state *r = data;
    struct zaws_head_headers fields = {0};
    if (h) {
        aws_http_headers_get(h, aws_byte_cursor_from_c_str("content-length"), &fields.length);
        aws_http_headers_get(h, aws_byte_cursor_from_c_str("last-modified"), &fields.modified);
        aws_http_headers_get(h, aws_byte_cursor_from_c_str("x-amz-storage-class"), &fields.storage_class);
        aws_http_headers_get(h, aws_byte_cursor_from_c_str("x-amz-restore"), &fields.restore);
        aws_http_headers_get(h, aws_byte_cursor_from_c_str("etag"), &fields.etag);
        fields.region_present = s_region_header(h, &fields.region);
        fields.checksum_type_present = aws_http_headers_get(h, aws_byte_cursor_from_c_str("x-amz-checksum-type"), &fields.checksum_type) == AWS_OP_SUCCESS;
        aws_http_headers_get(h, aws_byte_cursor_from_c_str("x-amz-checksum-crc32"), &fields.checksum_crc32);
        aws_http_headers_get(h, aws_byte_cursor_from_c_str("x-amz-checksum-crc32c"), &fields.checksum_crc32c);
        aws_http_headers_get(h, aws_byte_cursor_from_c_str("x-amz-checksum-crc64nvme"), &fields.checksum_crc64nvme);
        fields.checksum_reported = s_checksum_reported(h);
    }
    return r->headers ? r->headers(&fields, status, r->data) : AWS_OP_SUCCESS;
}
static int s_body(struct aws_s3_meta_request *m, const struct aws_byte_cursor *body, struct aws_s3_meta_request_receive_body_extra_info info, void *data) {
    struct request_state *r = data;
    struct aws_byte_cursor empty = {0};
    return r->body ? r->body(m, body ? *body : empty, info.range_start, info.ticket, r->data) : AWS_OP_SUCCESS;
}
static void s_finish(struct aws_s3_meta_request *m, const struct aws_s3_meta_request_result *result, void *data) {
    (void)m;
    struct request_state *r = data;
    struct zaws_result capture = { .error_code = AWS_ERROR_UNKNOWN };
    if (result) {
        capture.error_code = result->error_code;
        capture.response_status = result->response_status;
        if (result->error_response_body) capture.body = aws_byte_cursor_from_buf(result->error_response_body);
        if (result->error_response_operation_name) capture.operation = aws_byte_cursor_from_string(result->error_response_operation_name);
        capture.region_header_present = s_region_header(result->error_response_headers, &capture.region_header);
    }
    if (r->finish) r->finish(&capture, r->data);
}
static void s_shutdown(void *data) {
    struct request_state *r = data;
    if (r->shutdown) r->shutdown(r->data);
    s_request_free(r);
}
static void s_progress(struct aws_s3_meta_request *m, const struct aws_s3_meta_request_progress *progress, void *data) {
    (void)m;
    struct request_state *r = data;
    if (r->progress) r->progress(progress->bytes_transferred, r->data);
}
static struct aws_s3_meta_request_options s_request_meta_options(struct request_state *r, const struct aws_uri *endpoint) {
    struct aws_s3_meta_request_options opts = {0};
    opts.message = r->message; opts.endpoint = endpoint;
    opts.user_data = r; opts.finish_callback = s_finish; opts.shutdown_callback = s_shutdown;
    opts.progress_callback = r->progress ? s_progress : NULL;
    return opts;
}
static struct aws_s3_meta_request_options s_get_object_meta_options(struct request_state *r, const struct zaws_request_options *o, const struct aws_uri *endpoint) {
    struct aws_s3_meta_request_options opts = s_request_meta_options(r, endpoint);
    if (o->single_request) {
        /* A DEFAULT meta request sends the message as is: one GET without a Range, whose body
         * arrives at offset zero, or at the Content-Range start, into either sink. */
        opts.type = AWS_S3_META_REQUEST_TYPE_DEFAULT;
        opts.operation_name = aws_byte_cursor_from_c_str("GetObject");
    } else {
        opts.type = AWS_S3_META_REQUEST_TYPE_GET_OBJECT;
    }
    if (o->has_body_callback) {
        opts.body_callback_ex = s_body;
        /* A body callback gets parts in object order unless it asks otherwise, which holds every
         * completed part's pool buffer behind the slowest earlier one. The writers place each range
         * at its offset, so delivering parts as they complete frees those buffers. aws-c-s3 still
         * delivers in order when a whole-object checksum must hash the body in order. */
        opts.out_of_order_delivery = AWS_TRIBOOL_TRUE;
        if (o->check_object_size) opts.headers_callback = s_headers;
    } else { opts.recv_filepath = o->filepath; opts.recv_file_option = AWS_S3_RECV_FILE_CREATE_OR_REPLACE; opts.recv_file_delete_on_failure = false; }
    return opts;
}
static struct aws_s3_meta_request_options s_head_object_meta_options(struct request_state *r, const struct zaws_request_options *o, const struct aws_uri *endpoint) {
    struct aws_s3_meta_request_options opts = s_request_meta_options(r, endpoint);
    opts.type = AWS_S3_META_REQUEST_TYPE_DEFAULT;
    opts.operation_name = aws_byte_cursor_from_c_str(o->kind == ZAWS_REQUEST_HEAD_BUCKET ? "HeadBucket" : "HeadObject");
    opts.headers_callback = s_headers;
    return opts;
}
/* One DeleteObject as a DEFAULT meta request, which aws-c-s3 sends as given, as upstream's CRT
 * transfer manager sends it (s3transfer/crt.py `_default_get_make_request_args`). */
static struct aws_s3_meta_request_options s_delete_object_meta_options(struct request_state *r, const struct aws_uri *endpoint) {
    struct aws_s3_meta_request_options opts = s_request_meta_options(r, endpoint);
    opts.type = AWS_S3_META_REQUEST_TYPE_DEFAULT;
    opts.operation_name = aws_byte_cursor_from_c_str("DeleteObject");
    return opts;
}
static struct aws_s3_meta_request_options s_put_object_meta_options(struct request_state *r, const struct zaws_request_options *o, const struct aws_uri *endpoint) {
    struct aws_s3_meta_request_options opts = s_request_meta_options(r, endpoint);
    opts.type = AWS_S3_META_REQUEST_TYPE_PUT_OBJECT;
    opts.send_filepath = o->filepath;
    return opts;
}
static struct aws_s3_meta_request_options s_meta_options(struct request_state *r, const struct zaws_request_options *o, const struct aws_uri *endpoint) {
    switch (o->kind) {
    case ZAWS_REQUEST_GET: return s_get_object_meta_options(r, o, endpoint);
    case ZAWS_REQUEST_HEAD:
    case ZAWS_REQUEST_HEAD_BUCKET: return s_head_object_meta_options(r, o, endpoint);
    case ZAWS_REQUEST_DELETE: return s_delete_object_meta_options(r, endpoint);
    case ZAWS_REQUEST_PUT: break;
    }
    return s_put_object_meta_options(r, o, endpoint);
}
void zaws_request_option_snapshot(const struct zaws_request_options *o, struct zaws_option_snapshot *out) {
    struct request_state r = {0};
    struct aws_s3_meta_request_options opts = s_meta_options(&r, o, NULL);
    *out = (struct zaws_option_snapshot){ .kind = opts.type, .out_of_order = opts.out_of_order_delivery, .has_hint = opts.object_size_hint != NULL, .body = opts.body_callback_ex != NULL, .recv_delete = opts.recv_file_delete_on_failure, .progress = opts.progress_callback != NULL, .headers = opts.headers_callback != NULL, .hint = opts.object_size_hint ? *opts.object_size_hint : 0, .operation = opts.operation_name, .recv_path = opts.recv_filepath, .send_path = opts.send_filepath };
}
static void s_configure_checksum(struct zaws_runtime *runtime, struct request_state *r, const struct zaws_request_options *o, struct aws_s3_meta_request_options *opts) {
    if (o->kind == ZAWS_REQUEST_GET && (o->validate_checksum || runtime->response_checksum)) {
        r->checksum.validate_response_checksum = true;
        if (o->expected_checksum.len) {
            r->checksum.expected_checksum = o->expected_checksum;
            r->checksum.expected_checksum_algorithm = (enum aws_s3_checksum_algorithm)o->expected_checksum_algorithm;
        } else if (o->checksum_unavailable) {
            r->checksum.response_checksum_validation_mode = AWS_SCVM_REQUEST_ONLY;
        }
        opts->checksum_config = &r->checksum;
    } else if (o->kind == ZAWS_REQUEST_PUT && (o->checksum_algorithm != AWS_SCA_NONE || runtime->request_checksum)) {
        r->checksum.location = AWS_SCL_TRAILER;
        r->checksum.checksum_algorithm = o->checksum_algorithm != AWS_SCA_NONE ? (enum aws_s3_checksum_algorithm)o->checksum_algorithm : AWS_SCA_CRC64NVME;
        opts->checksum_config = &r->checksum;
    }
}
static void s_snapshot_progress(uint64_t bytes, void *data) { (void)bytes; (void)data; }
void zaws_configured_request_snapshot(struct zaws_runtime *runtime, const struct zaws_request_options *o, bool progress, struct zaws_configured_snapshot *out) {
    struct request_state r = { .progress = progress ? s_snapshot_progress : NULL };
    struct aws_s3_meta_request_options opts = s_meta_options(&r, o, &runtime->endpoint);
    s_configure_checksum(runtime, &r, o, &opts);
    *out = (struct zaws_configured_snapshot) {
        .meta = { .kind = opts.type, .out_of_order = opts.out_of_order_delivery, .has_hint = opts.object_size_hint != NULL, .body = opts.body_callback_ex != NULL, .recv_delete = opts.recv_file_delete_on_failure, .progress = opts.progress_callback != NULL, .headers = opts.headers_callback != NULL, .operation = opts.operation_name, .recv_path = opts.recv_filepath, .send_path = opts.send_filepath },
        .checksum_location = r.checksum.location, .checksum_algorithm = r.checksum.checksum_algorithm,
        .has_checksum = opts.checksum_config != NULL, .validate_response = r.checksum.validate_response_checksum,
        .validation_algorithms_null = r.checksum.validate_checksum_algorithms == NULL,
        .owns_checksum = opts.checksum_config == &r.checksum,
        .full_object_callback_null = r.checksum.full_object_checksum_callback == NULL,
        .validation_mode = r.checksum.response_checksum_validation_mode,
        .expected_checksum_algorithm = r.checksum.expected_checksum_algorithm,
        .expected_checksum = r.checksum.expected_checksum,
    };
}
int zaws_endpoint_request_path(struct aws_allocator *allocator, struct aws_byte_cursor base, struct aws_byte_cursor key, enum zaws_request_kind kind, struct aws_byte_buf *out) {
    if (aws_byte_buf_init(out, allocator, base.len + 1 + key.len)) return AWS_OP_ERR;
    if (aws_byte_buf_append_dynamic(out, &base)) goto fail;
    if (kind == ZAWS_REQUEST_HEAD_BUCKET) {
        if (!base.len && aws_byte_buf_append_byte_dynamic(out, '/')) goto fail;
    } else {
        if ((!base.len || base.ptr[base.len - 1] != '/') && aws_byte_buf_append_byte_dynamic(out, '/')) goto fail;
        if (aws_byte_buf_append_dynamic(out, &key)) goto fail;
    }
    return AWS_OP_SUCCESS;
fail:
    aws_byte_buf_clean_up(out);
    return AWS_OP_ERR;
}
static struct aws_input_stream *s_file_length_open(void *data, struct aws_allocator *allocator, const char *path) {
    (void)data;
    return aws_input_stream_new_from_file(allocator, path);
}
static int s_file_length_get(void *data, struct aws_input_stream *stream, int64_t *out) {
    (void)data;
    return aws_input_stream_get_length(stream, out);
}
static void s_file_length_release(void *data, struct aws_input_stream *stream) {
    (void)data;
    aws_input_stream_release(stream);
}
static const struct zaws_file_length_ops s_crt_file_length_ops = {
    .open = s_file_length_open, .get_length = s_file_length_get, .release = s_file_length_release,
};
int zaws_upload_length_with_ops(struct aws_allocator *allocator, struct aws_byte_cursor path, const struct zaws_file_length_ops *ops, uint64_t *out) {
    struct aws_string *filename = aws_string_new_from_cursor(allocator, &path);
    if (!filename) return AWS_OP_ERR;
    struct aws_input_stream *stream = ops->open(ops->data, allocator, aws_string_c_str(filename));
    aws_string_destroy(filename);
    if (!stream) return AWS_OP_ERR;
    int64_t length = 0;
    int rc = ops->get_length(ops->data, stream, &length);
    ops->release(ops->data, stream);
    if (length < 0) return aws_raise_error(AWS_ERROR_INVALID_ARGUMENT);
    if (rc) return AWS_OP_ERR;
    *out = (uint64_t)length;
    return AWS_OP_SUCCESS;
}
int zaws_upload_length(struct aws_allocator *allocator, struct aws_byte_cursor path, uint64_t *out) {
    return zaws_upload_length_with_ops(allocator, path, &s_crt_file_length_ops, out);
}
struct aws_s3_meta_request *zaws_submit(struct zaws_runtime *runtime, const struct zaws_request_options *o, zaws_headers_fn *headers, zaws_body_fn *body, zaws_finish_fn *finish, zaws_progress_fn *progress, aws_simple_completion_callback *shutdown, void *data) {
    struct request_state *r = aws_mem_calloc(runtime->allocator, 1, sizeof(*r));
    if (!r) return NULL;
    r->allocator = runtime->allocator;
    r->headers = headers; r->body = body; r->finish = finish; r->progress = progress; r->shutdown = shutdown; r->data = data;
    struct aws_byte_buf path = {0};
    if (zaws_endpoint_request_path(r->allocator, runtime->endpoint.path, o->key, o->kind, &path)) goto fail;
    struct aws_byte_cursor method;
    switch (o->kind) {
    case ZAWS_REQUEST_GET: method = aws_http_method_get; break;
    case ZAWS_REQUEST_PUT: method = aws_http_method_put; break;
    case ZAWS_REQUEST_DELETE: method = aws_http_method_delete; break;
    case ZAWS_REQUEST_HEAD:
    case ZAWS_REQUEST_HEAD_BUCKET:
    default: method = aws_http_method_head; break;
    }
    bool put = o->kind == ZAWS_REQUEST_PUT;
    uint64_t length = 0;
    if (put && zaws_upload_length(r->allocator, o->filepath, &length)) goto fail;
    struct aws_byte_cursor user_agent = o->user_agent.len ? o->user_agent : aws_byte_cursor_from_string(runtime->user_agent);
    r->message = zaws_message_new(runtime->endpoint.authority, aws_byte_cursor_from_buf(&path), method, put ? &length : NULL, put ? o->content_type : (struct aws_byte_cursor){0}, o->if_none_match, o->if_match, o->request_payer, o->headers, o->header_count, user_agent);
    aws_byte_buf_clean_up(&path);
    if (!r->message) goto fail;
    struct aws_s3_meta_request_options opts = s_meta_options(r, o, &runtime->endpoint);
    s_configure_checksum(runtime, r, o, &opts);
    struct aws_s3_meta_request *meta = aws_s3_client_make_meta_request(runtime->client, &opts);
    if (!meta) goto fail;
    return meta;
fail: {
    int error = aws_last_error();
    aws_byte_buf_clean_up(&path);
    s_request_free(r);
    aws_raise_error(error ? error : AWS_ERROR_UNKNOWN);
    return NULL;
}
}
void zaws_runtime_endpoint(struct zaws_runtime *runtime, struct aws_byte_cursor *authority, struct aws_byte_cursor *path) {
    *authority = runtime->endpoint.authority;
    *path = runtime->endpoint.path;
}
int zaws_message_add_header(struct aws_http_message *message, struct aws_byte_cursor name, struct aws_byte_cursor value) {
    struct aws_http_header header = { .name = name, .value = value };
    return aws_http_message_add_header(message, header);
}
static int s_message_body(struct aws_s3_meta_request *m, const struct aws_byte_cursor *body, uint64_t offset, void *data) {
    struct request_state *r = data;
    struct aws_byte_cursor empty = {0};
    return r->body ? r->body(m, body ? *body : empty, offset, NULL, r->data) : AWS_OP_SUCCESS;
}
static void s_message_telemetry(struct aws_s3_meta_request *m, struct aws_s3_request_metrics *metrics, void *data) {
    (void)m;
    struct request_state *r = data;
    int status = 0;
    if (aws_s3_request_metrics_get_response_status_code(metrics, &status)) status = 0;
    if (r->telemetry) r->telemetry(status, r->data);
}
struct aws_s3_meta_request *zaws_submit_message(struct zaws_runtime *runtime, struct aws_http_message *message, struct aws_byte_cursor operation, zaws_body_fn *body, zaws_finish_fn *finish, zaws_telemetry_fn *telemetry, aws_simple_completion_callback *shutdown, void *data) {
    struct request_state *r = aws_mem_calloc(runtime->allocator, 1, sizeof(*r));
    if (!r) return NULL;
    r->allocator = runtime->allocator;
    r->message = aws_http_message_acquire(message);
    r->body = body; r->finish = finish; r->telemetry = telemetry; r->shutdown = shutdown; r->data = data;
    struct aws_s3_meta_request_options opts = {0};
    opts.type = AWS_S3_META_REQUEST_TYPE_DEFAULT;
    opts.operation_name = operation;
    opts.signing_config = &runtime->signing;
    opts.message = r->message; opts.endpoint = &runtime->endpoint;
    opts.user_data = r; opts.body_callback = s_message_body; opts.finish_callback = s_finish;
    opts.telemetry_callback = s_message_telemetry; opts.shutdown_callback = s_shutdown;
    struct aws_s3_meta_request *meta = aws_s3_client_make_meta_request(runtime->client, &opts);
    if (!meta) s_request_free(r);
    return meta;
}
/* Keep pool storage fallible: aws_mem_calloc aborts when an allocator returns NULL. */
void *zaws_allocate_zeroed(struct aws_allocator *allocator, size_t count, size_t size) {
    AWS_FATAL_PRECONDITION(allocator != NULL);
    AWS_FATAL_PRECONDITION(count != 0 && size != 0);
    AWS_FATAL_PRECONDITION(allocator->mem_calloc || allocator->mem_acquire);
    if (count > SIZE_MAX / size) return NULL;
    if (allocator->mem_calloc) return allocator->mem_calloc(allocator, count, size);
    const size_t bytes = count * size;
    void *memory = allocator->mem_acquire(allocator, bytes);
    if (memory) memset(memory, 0, bytes);
    return memory;
}

struct allocator_adapter { struct aws_allocator allocator; void *(*acquire)(void *, size_t); void (*release)(void *, void *); void *data; };
static void *s_acquire(struct aws_allocator *allocator, size_t size) { struct allocator_adapter *a = allocator->impl; return a->acquire(a->data, size); }
static void s_release(struct aws_allocator *allocator, void *ptr) { struct allocator_adapter *a = allocator->impl; a->release(a->data, ptr); }
struct aws_allocator *zaws_allocator_new(void *(*acquire)(void *, size_t), void (*release)(void *, void *), void *data) {
    struct allocator_adapter *a = aws_mem_calloc(rust_crt_allocator(), 1, sizeof(*a));
    if (!a) return NULL;
    a->acquire = acquire; a->release = release; a->data = data;
    a->allocator.mem_acquire = s_acquire; a->allocator.mem_release = s_release; a->allocator.impl = a;
    return &a->allocator;
}
void zaws_allocator_destroy(struct aws_allocator *a) { aws_mem_release(rust_crt_allocator(), a); }
/* The standard logger's stderr writer and formatter on a foreground channel, which writes
 * each record on the thread that logs it. The standard logger's background channel writes
 * from its own thread, so its records could reach stderr after lines the CLI wrote later,
 * such as a listing summary printed once the runtime has shut down. */
struct zaws_logger {
    struct aws_logger logger;
    struct aws_log_writer writer;
    struct aws_log_formatter formatter;
    struct aws_log_channel channel;
};
void *zaws_logger_new(void) {
    struct aws_allocator *allocator = rust_crt_allocator();
    struct zaws_logger *l = aws_mem_calloc(allocator, 1, sizeof(*l));
    if (!l) return NULL;
    struct aws_log_writer_file_options writer = { .file = stderr };
    struct aws_log_formatter_standard_options formatter = { .date_format = AWS_DATE_FORMAT_ISO_8601 };
    if (aws_log_writer_init_file(&l->writer, allocator, &writer)) goto writer_failed;
    if (aws_log_formatter_init_default(&l->formatter, allocator, &formatter)) goto formatter_failed;
    if (aws_log_channel_init_foreground(&l->channel, allocator, &l->writer)) goto channel_failed;
    if (aws_logger_init_from_external(&l->logger, allocator, &l->formatter, &l->channel, &l->writer, AWS_LL_DEBUG)) goto logger_failed;
    aws_logger_set(&l->logger); return l;
logger_failed: aws_log_channel_clean_up(&l->channel);
channel_failed: aws_log_formatter_clean_up(&l->formatter);
formatter_failed: aws_log_writer_clean_up(&l->writer);
writer_failed: aws_mem_release(allocator, l); return NULL;
}
/* aws_logger_clean_up releases only the logger of an external pipeline. */
void zaws_logger_destroy(void *ptr) {
    struct zaws_logger *l = ptr;
    if (!l) return;
    aws_logger_set(NULL); aws_logger_clean_up(&l->logger);
    aws_log_channel_clean_up(&l->channel); aws_log_formatter_clean_up(&l->formatter); aws_log_writer_clean_up(&l->writer);
    aws_mem_release(rust_crt_allocator(), l);
}
void zaws_debug_emit(struct aws_byte_cursor logger, const char *message) {
    struct aws_date_time now;
    aws_date_time_init_now(&now);
    fprintf(stderr, "%04u-%02u-%02u %02u:%02u:%02u,%03u - %.*s - DEBUG - %s\n",
        aws_date_time_year(&now, true), aws_date_time_month(&now, true) + 1,
        aws_date_time_month_day(&now, true), aws_date_time_hour(&now, true),
        aws_date_time_minute(&now, true), aws_date_time_second(&now, true),
        (unsigned)(aws_date_time_as_millis(&now) % 1000), (int)logger.len, logger.ptr, message);
}
void zaws_proxy_snapshot(struct zaws_runtime *r, struct zaws_proxy_snapshot *out) {
    const struct aws_http_proxy_options *p = &r->proxy.options;
    *out = (struct zaws_proxy_snapshot){ .host = p->host, .port = p->port, .connection_type = p->connection_type, .strategy = p->proxy_strategy != NULL, .tls = p->tls_options != NULL, .env_disabled = r->s3_proxy_env.env_var_type == AWS_HPEV_DISABLE, .configured = s_proxy_connection_options(&r->proxy) != NULL };
}
bool zaws_runtime_has_custom_tls(struct zaws_runtime *runtime) { return runtime->tls != NULL; }
int zaws_callback_capture(const struct aws_byte_cursor *names, const struct aws_byte_cursor *values, size_t count, int status, int error_code, zaws_headers_fn *headers, zaws_finish_fn *finish, void *data) {
    struct aws_http_headers *h = aws_http_headers_new(rust_crt_allocator());
    if (!h) return AWS_OP_ERR;
    for (size_t i = 0; i < count; i++) {
        if (aws_http_headers_add(h, names[i], values[i])) { aws_http_headers_release(h); return AWS_OP_ERR; }
    }
    struct request_state r = { .headers = headers, .finish = finish, .data = data };
    int rc = s_headers(NULL, h, status, &r);
    struct aws_s3_meta_request_result result = { .error_response_headers = h, .response_status = status, .error_code = error_code };
    s_finish(NULL, &result, &r);
    aws_http_headers_release(h);
    return rc;
}
