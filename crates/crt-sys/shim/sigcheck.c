#include "native.h"
#include <aws/auth/auth.h>
#include <aws/common/allocator.h>
#include <aws/common/cross_process_lock.h>
#include <aws/common/error.h>
#include <aws/common/ref_count.h>
#include <aws/io/io.h>
#include <aws/io/stream.h>
#include <aws/s3/s3.h>
#include <stddef.h>
#define LAYOUT(type, size) _Static_assert(sizeof(struct type) == size, #type " size")
#define OFFSET(type, field, value) _Static_assert(offsetof(struct type, field) == value, #type "." #field " offset")
LAYOUT(aws_byte_cursor,16); OFFSET(aws_byte_cursor,ptr,8);
LAYOUT(aws_byte_buf,32); OFFSET(aws_byte_buf,allocator,24);
LAYOUT(aws_ref_count,24);
LAYOUT(aws_s3_buffer_ticket,40); OFFSET(aws_s3_buffer_ticket,impl,32);
LAYOUT(aws_s3_buffer_ticket_vtable,24);
LAYOUT(aws_s3_buffer_pool,40); OFFSET(aws_s3_buffer_pool,impl,32);
LAYOUT(aws_s3_buffer_pool_vtable,72);
LAYOUT(aws_s3_buffer_pool_reserve_meta,40);
LAYOUT(aws_s3_buffer_pool_config,32);
LAYOUT(aws_s3_meta_request_receive_body_extra_info,16);
LAYOUT(aws_s3_meta_request_result,40); OFFSET(aws_s3_meta_request_result,error_code,36);
LAYOUT(zaws_runtime_options,200); OFFSET(zaws_runtime_options,pool_factory,96);
OFFSET(zaws_runtime_options,verify_peer,176); OFFSET(zaws_runtime_options,credentials_delegate,184);
LAYOUT(zaws_credentials_view,72); OFFSET(zaws_credentials_view,expiration_timepoint_seconds,64);
LAYOUT(zaws_http_options,112); OFFSET(zaws_http_options,headers,80); OFFSET(zaws_http_options,port,96); OFFSET(zaws_http_options,connect_timeout_ms,100);
OFFSET(zaws_http_options,tls,104);
LAYOUT(zaws_runtime_snapshot,72); OFFSET(zaws_runtime_snapshot,anonymous,60);
LAYOUT(zaws_signing_snapshot,56);
LAYOUT(zaws_credentials_snapshot,1);
LAYOUT(zaws_request_options,152); OFFSET(zaws_request_options,checksum_algorithm,4);
OFFSET(zaws_request_options,single_request,40); OFFSET(zaws_request_options,check_object_size,43);
OFFSET(zaws_request_options,validate_checksum,44); OFFSET(zaws_request_options,content_type,48);
OFFSET(zaws_request_options,if_match,64);
OFFSET(zaws_request_options,request_payer,80); OFFSET(zaws_request_options,user_agent,96);
OFFSET(zaws_request_options,headers,112); OFFSET(zaws_request_options,header_count,120);
OFFSET(zaws_request_options,expected_checksum,128); OFFSET(zaws_request_options,expected_checksum_algorithm,144);
OFFSET(zaws_request_options,checksum_unavailable,148);
LAYOUT(zaws_header,32); OFFSET(zaws_header,value,16);
LAYOUT(zaws_result,64); OFFSET(zaws_result,region_header_present,56);
LAYOUT(zaws_head_headers,168); OFFSET(zaws_head_headers,checksum_type,96);
OFFSET(zaws_head_headers,region_present,160); OFFSET(zaws_head_headers,checksum_reported,162);
_Static_assert(AWS_ERROR_S3_SLOW_DOWN == 0x3806, "slow down code");
_Static_assert(AWS_ERROR_S3_INVALID_RESPONSE_STATUS == 0x3807, "invalid response status code");
_Static_assert(AWS_ERROR_S3_CANCELED == 0x380B, "canceled code");
_Static_assert(AWS_ERROR_S3_RESPONSE_CHECKSUM_MISMATCH == 0x380E, "checksum mismatch code");
_Static_assert(AWS_ERROR_S3_OBJECT_MODIFIED == 0x3814, "object modified code");
_Static_assert(AWS_ERROR_S3_BUFFER_ALLOCATION_FAILED == 0x3822, "buffer allocation code");
_Static_assert(AWS_ERROR_FILE_INVALID_PATH == 44, "invalid path code");
_Static_assert(AWS_AUTH_SIGNING_NO_CREDENTIALS == 6146, "no credentials code");
_Static_assert(AWS_IO_TLS_ERROR_NEGOTIATION_FAILURE == 1029 && AWS_IO_TLS_NEGOTIATION_TIMEOUT == 1067, "TLS negotiation codes");
_Static_assert(AWS_IO_SOCKET_CONNECTION_REFUSED == 1047 && AWS_IO_SOCKET_TIMEOUT == 1048, "socket codes");
_Static_assert(AWS_IO_SOCKET_NO_ROUTE_TO_HOST == 1049 && AWS_IO_SOCKET_NETWORK_DOWN == 1050, "socket codes");
_Static_assert(AWS_IO_SOCKET_CONNECT_ABORTED == 1057 && AWS_IO_DNS_QUERY_FAILED == 1058, "connection codes");
_Static_assert(AWS_IO_DNS_INVALID_NAME == 1059 && AWS_IO_DNS_NO_ADDRESS_FOR_HOST == 1060, "DNS codes");
#ifdef ZAWS_INJECT_LAYOUT_MISMATCH
LAYOUT(aws_byte_cursor,17);
#endif
#ifdef ZAWS_INJECT_SIGNATURE_MISMATCH
static void (*signature_failure)(int) = aws_s3_meta_request_cancel;
#endif
#define CHECK(name, result, ...) static result (*const check_##name)(__VA_ARGS__) = name
CHECK(aws_s3_meta_request_release, struct aws_s3_meta_request *,struct aws_s3_meta_request *);
CHECK(aws_s3_meta_request_cancel, void,struct aws_s3_meta_request *);
CHECK(aws_s3_buffer_ticket_acquire, struct aws_s3_buffer_ticket *,struct aws_s3_buffer_ticket *);
CHECK(aws_s3_buffer_ticket_release, struct aws_s3_buffer_ticket *,struct aws_s3_buffer_ticket *);
CHECK(aws_future_s3_buffer_ticket_get_error,int,const struct aws_future_s3_buffer_ticket *);
CHECK(aws_future_s3_buffer_ticket_new, struct aws_future_s3_buffer_ticket *,struct aws_allocator *);
CHECK(aws_future_s3_buffer_ticket_acquire, struct aws_future_s3_buffer_ticket *,struct aws_future_s3_buffer_ticket *);
CHECK(aws_future_s3_buffer_ticket_release, struct aws_future_s3_buffer_ticket *,struct aws_future_s3_buffer_ticket *);
CHECK(aws_future_s3_buffer_ticket_set_result_by_move, void,struct aws_future_s3_buffer_ticket *,struct aws_s3_buffer_ticket **);
CHECK(aws_future_s3_buffer_ticket_set_error, void,struct aws_future_s3_buffer_ticket *,int);
CHECK(aws_future_s3_buffer_ticket_is_done, bool,const struct aws_future_s3_buffer_ticket *);
CHECK(aws_raise_error, int,int);
CHECK(aws_cross_process_lock_try_acquire, struct aws_cross_process_lock *,struct aws_allocator *,struct aws_byte_cursor);
CHECK(aws_cross_process_lock_release, void,struct aws_cross_process_lock *);
CHECK(aws_mem_calloc, void *,struct aws_allocator *,size_t,size_t);
CHECK(zaws_allocate_zeroed, void *,struct aws_allocator *,size_t,size_t);
CHECK(aws_mem_release, void,struct aws_allocator *,void *);
CHECK(aws_http_message_release, struct aws_http_message *,struct aws_http_message *);
CHECK(aws_http_message_get_header_count, size_t,const struct aws_http_message *);
CHECK(aws_s3_default_memory_limit_for_throughput, size_t,double);
CHECK(aws_byte_buf_clean_up, void,struct aws_byte_buf *);
CHECK(zaws_endpoint_request_path, int,struct aws_allocator *,struct aws_byte_cursor,struct aws_byte_cursor,enum zaws_request_kind,struct aws_byte_buf *);
CHECK(zaws_upload_length_with_ops, int,struct aws_allocator *,struct aws_byte_cursor,const struct zaws_file_length_ops *,uint64_t *);
CHECK(zaws_upload_length, int,struct aws_allocator *,struct aws_byte_cursor,uint64_t *);
CHECK(zaws_credentials_complete, void,aws_on_get_credentials_callback_fn *,void *,const struct zaws_credentials_view *);
CHECK(zaws_http_request, struct zaws_http_call *,struct zaws_runtime *,const struct zaws_http_options *,zaws_http_event_fn *,zaws_http_finish_fn *,void *);
CHECK(zaws_http_cancel, void,struct zaws_http_call *);
CHECK(zaws_http_release, void,struct zaws_http_call *);
LAYOUT(zaws_file_length_ops,32); OFFSET(zaws_file_length_ops,data,24);
LAYOUT(zaws_option_snapshot,72); OFFSET(zaws_option_snapshot,out_of_order,4);
OFFSET(zaws_option_snapshot,headers,12); OFFSET(zaws_option_snapshot,hint,16); LAYOUT(zaws_proxy_snapshot,32);
LAYOUT(zaws_configured_snapshot,112); OFFSET(zaws_configured_snapshot,validation_mode,88);
OFFSET(zaws_configured_snapshot,expected_checksum,96);
_Static_assert(AWS_SCL_TRAILER == 2, "checksum trailer location");
_Static_assert(AWS_SCA_NONE == 0 && AWS_SCA_CRC32C == 1 && AWS_SCA_CRC32 == 2 && AWS_SCA_SHA1 == 3, "checksum algorithms");
_Static_assert(AWS_SCA_SHA256 == 4 && AWS_SCA_CRC64NVME == 5 && AWS_SCA_SHA512 == 6, "checksum algorithms");
_Static_assert(AWS_SCA_XXHASH64 == 7 && AWS_SCA_XXHASH3_64 == 8 && AWS_SCA_XXHASH3_128 == 9, "checksum algorithms");
_Static_assert(AWS_SCVM_DEFAULT == 0 && AWS_SCVM_REQUEST_ONLY == 1, "checksum validation modes");
_Static_assert(AWS_ERROR_UNKNOWN == 3, "unknown error code");
_Static_assert(AWS_ERROR_SUCCESS == 0 && AWS_ERROR_OOM == 1, "success and out-of-memory codes");
_Static_assert(AWS_ERROR_INVALID_ARGUMENT == 34, "invalid argument code");
_Static_assert(AWS_TRIBOOL_UNSET == 0 && AWS_TRIBOOL_TRUE == 2, "tribool values");
_Static_assert(ZAWS_TRUST_FILE_REJECTED == 1 && AWS_OP_ERR != 1, "trust file stage status");
_Static_assert(ZAWS_CLIENT_FAILED_WITH_PROXY == 2, "proxied client stage status");
_Static_assert(sizeof(enum zaws_runtime_stage) == 4, "stage size");
_Static_assert(ZAWS_STAGE_ENDPOINT == 0 && ZAWS_STAGE_REGION == 1 && ZAWS_STAGE_EVENT_LOOP == 2 && ZAWS_STAGE_RESOLVER == 3, "stage values");
_Static_assert(ZAWS_STAGE_BOOTSTRAP == 4 && ZAWS_STAGE_TLS == 5 && ZAWS_STAGE_CREDENTIALS == 6 && ZAWS_STAGE_CLIENT == 7, "stage values");
_Static_assert(sizeof(enum zaws_request_kind) == 4, "request kind size");
_Static_assert(ZAWS_REQUEST_GET == 0 && ZAWS_REQUEST_HEAD == 1 && ZAWS_REQUEST_PUT == 2 && ZAWS_REQUEST_HEAD_BUCKET == 3, "request kind values");
#include <aws/sdkutils/endpoints_rule_engine.h>
#include <aws/sdkutils/partitions.h>
#include <aws/sdkutils/sdkutils.h>
CHECK(aws_sdkutils_library_init,void,struct aws_allocator *);
CHECK(aws_sdkutils_library_clean_up,void,void);
CHECK(aws_endpoints_ruleset_new_from_string,struct aws_endpoints_ruleset *,struct aws_allocator *,struct aws_byte_cursor);
CHECK(aws_endpoints_ruleset_release,struct aws_endpoints_ruleset *,struct aws_endpoints_ruleset *);
CHECK(aws_partitions_config_new_from_string,struct aws_partitions_config *,struct aws_allocator *,struct aws_byte_cursor);
CHECK(aws_partitions_config_release,struct aws_partitions_config *,struct aws_partitions_config *);
CHECK(aws_endpoints_rule_engine_new,struct aws_endpoints_rule_engine *,struct aws_allocator *,struct aws_endpoints_ruleset *,struct aws_partitions_config *);
CHECK(aws_endpoints_rule_engine_release,struct aws_endpoints_rule_engine *,struct aws_endpoints_rule_engine *);
CHECK(aws_endpoints_request_context_new,struct aws_endpoints_request_context *,struct aws_allocator *);
CHECK(aws_endpoints_request_context_release,struct aws_endpoints_request_context *,struct aws_endpoints_request_context *);
CHECK(aws_endpoints_request_context_add_string,int,struct aws_allocator *,struct aws_endpoints_request_context *,struct aws_byte_cursor,struct aws_byte_cursor);
CHECK(aws_endpoints_request_context_add_boolean,int,struct aws_allocator *,struct aws_endpoints_request_context *,struct aws_byte_cursor,bool);
CHECK(aws_endpoints_rule_engine_resolve,int,struct aws_endpoints_rule_engine *,const struct aws_endpoints_request_context *,struct aws_endpoints_resolved_endpoint **);
CHECK(aws_endpoints_resolved_endpoint_get_type,enum aws_endpoints_resolved_endpoint_type,const struct aws_endpoints_resolved_endpoint *);
CHECK(aws_endpoints_resolved_endpoint_get_url,int,const struct aws_endpoints_resolved_endpoint *,struct aws_byte_cursor *);
CHECK(aws_endpoints_resolved_endpoint_get_properties,int,const struct aws_endpoints_resolved_endpoint *,struct aws_byte_cursor *);
CHECK(aws_endpoints_resolved_endpoint_get_error,int,const struct aws_endpoints_resolved_endpoint *,struct aws_byte_cursor *);
CHECK(aws_endpoints_resolved_endpoint_release,struct aws_endpoints_resolved_endpoint *,struct aws_endpoints_resolved_endpoint *);
_Static_assert(AWS_ENDPOINTS_RESOLVED_ERROR == 1,"endpoint rule error type");

LAYOUT(zaws_date,32); OFFSET(zaws_date,epoch_seconds,24);
CHECK(aws_xml_node_get_name,struct aws_byte_cursor,const struct aws_xml_node *);
CHECK(aws_xml_node_as_body,int,struct aws_xml_node *,struct aws_byte_cursor *);
CHECK(aws_xml_node_traverse,int,struct aws_xml_node *,aws_xml_parser_on_node_encountered_fn *,void *);
