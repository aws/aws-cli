#ifndef ZAWS_NATIVE_H
#define ZAWS_NATIVE_H
#include "crt_shim.h"
#include <aws/common/xml_parser.h>
struct zaws_runtime;
struct zaws_runtime_snapshot {
    uint64_t part_size, max_part_size, multipart_threshold, memory_limit;
    double throughput_gbps, disk_gbps;
    uint32_t max_connections, connect_timeout_ms, max_retries;
    bool anonymous, shared_tls, verify_peer, keep_alive, file_io, stream, direct;
    bool request_checksum, response_checksum;
};
void zaws_runtime_snapshot(struct zaws_runtime *, struct zaws_runtime_snapshot *);
struct zaws_signing_snapshot {
    struct aws_byte_cursor region, service, body;
    int validation;
    bool chain, provider, anonymous, same_credentials;
};
void zaws_runtime_signing_snapshot(struct zaws_runtime *, struct zaws_signing_snapshot *);
struct zaws_credentials_snapshot {
    bool delegate;
};
void zaws_credentials_snapshot(struct zaws_runtime *, struct zaws_credentials_snapshot *);
bool zaws_runtime_has_custom_tls(struct zaws_runtime *runtime);
bool zaws_platform(double *recommended_gbps);
struct zaws_runtime_options {
    struct aws_byte_cursor endpoint, region, signing_region, proxy_url;
    const char *ca_bundle;
    double throughput_target_gbps;
    uint64_t memory_limit;
    uint32_t max_connections;
    uint16_t event_loop_count;
    aws_s3_buffer_pool_factory_fn *pool_factory;
    void *pool_data;
    struct aws_byte_cursor ca_pem, user_agent;
    uint64_t part_size, multipart_upload_threshold;
    double disk_throughput_gbps;
    uint32_t max_attempts, connect_timeout_ms;
    bool verify_peer, no_sign_request, keep_alive;
    bool has_file_io, file_should_stream, file_direct_io;
    bool request_checksum, response_checksum;
    /* The CLI's own credentials, which a signed runtime needs: without one its credentials stage
     * fails with AWS_ERROR_INVALID_ARGUMENT. The CRT calls it for every request it signs, on its
     * own threads; `credentials_delegate_data` must stay valid until the credentials stage's
     * shutdown callback. */
    aws_credentials_provider_delegate_get_credentials_fn *credentials_delegate;
    void *credentials_delegate_data;
};
/* Credentials a delegate answers a query with, borrowed for the call. An empty session token or
 * account id is absent, and UINT64_MAX seconds since the epoch is no expiry. The expiry is carried,
 * not acted on: neither the signer nor the S3 client reads it, and the CRT caches nothing between
 * queries, so the delegate's owner decides when credentials are stale. */
struct zaws_credentials_view {
    struct aws_byte_cursor access_key_id, secret_access_key, session_token, account_id;
    uint64_t expiration_timepoint_seconds;
};
/* Answers one query a delegate received, exactly once, from any thread, during the delegate's call
 * or after it. A NULL view, or one the CRT refuses, reports a failure, which the signer turns into
 * AWS_AUTH_SIGNING_NO_CREDENTIALS whatever the code. */
void zaws_credentials_complete(aws_on_get_credentials_callback_fn *, void *callback_data, const struct zaws_credentials_view *);
struct zaws_result {
    int error_code, response_status;
    struct aws_byte_cursor body, operation, region_header;
    bool region_header_present;
};
enum zaws_request_kind {
    ZAWS_REQUEST_GET = 0,
    ZAWS_REQUEST_HEAD = 1,
    ZAWS_REQUEST_PUT = 2,
    ZAWS_REQUEST_HEAD_BUCKET = 3,
    ZAWS_REQUEST_DELETE = 4,
};
struct zaws_header {
    struct aws_byte_cursor name, value;
};
struct zaws_request_options {
    enum zaws_request_kind kind;
    int checksum_algorithm;
    struct aws_byte_cursor key, filepath;
    bool single_request, has_body_callback, if_none_match, check_object_size;
    bool validate_checksum;
    struct aws_byte_cursor content_type, if_match, request_payer, user_agent;
    const struct zaws_header *headers;
    size_t header_count;
    /* What a GET that validates its response checksum knows of the object's full-object checksum,
     * as s3transfer/crt.py `_configure_full_object_checksum_validation` hands it to the CRT: a
     * nonempty expected_checksum, the base64 of an expected_checksum_algorithm digest (an
     * `aws_s3_checksum_algorithm`), is validated in place of the one the CRT would look up, and
     * otherwise checksum_unavailable validates each response against its own checksum alone. Either
     * saves the HeadObject the CRT sends to learn the checksum. A GET that does not validate ignores
     * both; expected_checksum is borrowed for the synchronous submit. */
    struct aws_byte_cursor expected_checksum;
    int expected_checksum_algorithm;
    bool checksum_unavailable;
};
struct zaws_head_headers {
    struct aws_byte_cursor length, modified, storage_class, restore, etag, region;
    struct aws_byte_cursor checksum_type, checksum_crc32, checksum_crc32c, checksum_crc64nvme;
    bool region_present, checksum_type_present;
    bool checksum_reported;
};
typedef int(zaws_headers_fn)(const struct zaws_head_headers *, int status, void *data);
typedef int(zaws_body_fn)(struct aws_s3_meta_request *, struct aws_byte_cursor body, uint64_t offset, struct aws_s3_buffer_ticket *, void *data);
typedef void(zaws_finish_fn)(const struct zaws_result *, void *data);
typedef void(zaws_progress_fn)(uint64_t bytes, void *data);
/* One request over aws-c-http on the runtime's bootstrap, outside aws-c-s3: the path a call to
 * any other service takes, a credential provider's own among them. Everything is borrowed for
 * the call.
 *
 * `host` and `port` are where to connect, in plaintext, and `method`, `target` and `headers` are
 * the request as it is sent, the Host header included; it has no body. A nonempty `service` signs
 * it with SigV4 for that service in `region`, through the provider the runtime's credentials
 * stage built. The process environment's proxies are never read: a caller with a proxy connects
 * to it and sends an absolute `target`.
 *
 * `connect_timeout_ms` bounds the connect. Nothing here bounds the response: the caller watches
 * the events and cancels. */
struct zaws_http_options {
    struct aws_byte_cursor host, method, target, region, service;
    const struct zaws_header *headers;
    size_t header_count;
    uint32_t port, connect_timeout_ms;
    /* Connects with TLS: the runtime's trust and peer verification, the server named `host`, and
     * `connect_timeout_ms` again as the bound of the handshake. */
    bool tls;
};
/* What a call reports before it finishes, each on a CRT thread, which must not wait. */
enum zaws_http_event {
    /* The connection is up and aws-c-http has taken the request to send. */
    ZAWS_HTTP_CONNECTED = 0,
    /* Some of the response's headers arrived. */
    ZAWS_HTTP_HEADERS = 1,
    /* Some of the response's body arrived: `body`, borrowed for the callback. */
    ZAWS_HTTP_BODY = 2,
};
typedef void(zaws_http_event_fn)(int event, struct aws_byte_cursor body, void *data);
/* `status` is the response's when `error_code` is 0. */
typedef void(zaws_http_finish_fn)(int error_code, int status, void *data);
struct zaws_http_call;
/* Starts the request. NULL, with the CRT's error raised and no callback, when it could not start.
 * Otherwise `finish` runs exactly once, after every event, on the calling thread or a CRT thread
 * and possibly before this returns, and the caller owns one reference to the call. The runtime's
 * bootstrap stage waits for a call in flight, so `data` outlives the runtime only if the caller
 * keeps it. */
struct zaws_http_call *zaws_http_request(struct zaws_runtime *, const struct zaws_http_options *, zaws_http_event_fn *, zaws_http_finish_fn *, void *data);
/* Abandons the call from any thread: closes its connection, now or as soon as it is up. `finish`
 * still runs, with whatever error the close left. A connect in progress cannot be interrupted,
 * nor can the TLS handshake that follows it; each has `connect_timeout_ms`. */
void zaws_http_cancel(struct zaws_http_call *);
/* Gives up the caller's reference. */
void zaws_http_release(struct zaws_http_call *);
struct zaws_runtime *zaws_runtime_allocate(void);
enum zaws_runtime_stage {
    ZAWS_STAGE_ENDPOINT = 0,
    ZAWS_STAGE_REGION = 1,
    ZAWS_STAGE_EVENT_LOOP = 2,
    ZAWS_STAGE_RESOLVER = 3,
    ZAWS_STAGE_BOOTSTRAP = 4,
    ZAWS_STAGE_TLS = 5,
    ZAWS_STAGE_CREDENTIALS = 6,
    ZAWS_STAGE_CLIENT = 7,
};
#define ZAWS_TRUST_FILE_REJECTED 1
#define ZAWS_CLIENT_FAILED_WITH_PROXY 2
int zaws_runtime_start_stage(struct zaws_runtime *, enum zaws_runtime_stage, const struct zaws_runtime_options *, aws_simple_completion_callback *, void *);
void zaws_runtime_release_stage(struct zaws_runtime *, enum zaws_runtime_stage);
void zaws_runtime_destroy(struct zaws_runtime *);
struct aws_s3_meta_request *zaws_submit(struct zaws_runtime *, const struct zaws_request_options *, zaws_headers_fn *, zaws_body_fn *, zaws_finish_fn *, zaws_progress_fn *, aws_simple_completion_callback *, void *);
int zaws_endpoint_request_path(struct aws_allocator *, struct aws_byte_cursor base, struct aws_byte_cursor key, enum zaws_request_kind, struct aws_byte_buf *out);
struct aws_input_stream;
struct zaws_file_length_ops {
    struct aws_input_stream *(*open)(void *data, struct aws_allocator *, const char *path);
    int (*get_length)(void *data, struct aws_input_stream *, int64_t *out);
    void (*release)(void *data, struct aws_input_stream *);
    void *data;
};
int zaws_upload_length_with_ops(struct aws_allocator *, struct aws_byte_cursor path, const struct zaws_file_length_ops *, uint64_t *out);
int zaws_upload_length(struct aws_allocator *, struct aws_byte_cursor path, uint64_t *out);
void zaws_runtime_endpoint(struct zaws_runtime *, struct aws_byte_cursor *, struct aws_byte_cursor *);
int zaws_message_add_header(struct aws_http_message *, struct aws_byte_cursor, struct aws_byte_cursor);
typedef void(zaws_telemetry_fn)(int status, void *data);
struct aws_s3_meta_request *zaws_submit_message(struct zaws_runtime *, struct aws_http_message *, struct aws_byte_cursor operation, zaws_body_fn *, zaws_finish_fn *, zaws_telemetry_fn *, aws_simple_completion_callback *, void *);
struct aws_http_message *zaws_message_new(struct aws_byte_cursor host, struct aws_byte_cursor path, struct aws_byte_cursor method, const uint64_t *length, struct aws_byte_cursor content_type, bool if_none_match, struct aws_byte_cursor if_match, struct aws_byte_cursor request_payer, const struct zaws_header *headers, size_t header_count, struct aws_byte_cursor user_agent);
int zaws_message_field(const struct aws_http_message *, unsigned index, struct aws_byte_cursor *, struct aws_byte_cursor *);
int zaws_parse_http_date(struct aws_byte_cursor, int64_t *);
struct zaws_date { int fields[6]; int64_t epoch_seconds; };
int zaws_parse_date(struct aws_byte_cursor, struct zaws_date *);
int zaws_xml_parse(struct aws_byte_cursor, aws_xml_parser_on_node_encountered_fn *, void *);
int zaws_xml_unescape(struct aws_byte_cursor text, uint8_t *out, size_t *out_len);
int zaws_listing_error(unsigned kind);
void *zaws_allocate_zeroed(struct aws_allocator *, size_t count, size_t size);
struct aws_allocator *zaws_allocator_new(void *(*acquire)(void *, size_t), void (*release)(void *, void *), void *);
void zaws_allocator_destroy(struct aws_allocator *);
void *zaws_logger_new(void);
void zaws_logger_destroy(void *);
void zaws_debug_emit(struct aws_byte_cursor, const char *);
struct zaws_option_snapshot { int kind, out_of_order; bool has_hint, body, recv_delete, progress, headers; uint64_t hint; struct aws_byte_cursor operation, recv_path, send_path; };
void zaws_request_option_snapshot(const struct zaws_request_options *, struct zaws_option_snapshot *);
struct zaws_configured_snapshot {
    struct zaws_option_snapshot meta;
    int checksum_location, checksum_algorithm;
    bool has_checksum, validate_response, validation_algorithms_null, owns_checksum;
    bool full_object_callback_null;
    int validation_mode, expected_checksum_algorithm;
    struct aws_byte_cursor expected_checksum;
};
void zaws_configured_request_snapshot(struct zaws_runtime *, const struct zaws_request_options *, bool, struct zaws_configured_snapshot *);
struct zaws_proxy_snapshot { struct aws_byte_cursor host; uint32_t port; int connection_type; bool strategy, tls, env_disabled, configured; };
void zaws_proxy_snapshot(struct zaws_runtime *, struct zaws_proxy_snapshot *);
int zaws_callback_capture(const struct aws_byte_cursor *names, const struct aws_byte_cursor *values, size_t count, int status, int error_code, zaws_headers_fn *, zaws_finish_fn *, void *);
#endif
