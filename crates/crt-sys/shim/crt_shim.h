#ifndef AWS_CLI_NATIVE_CRT_SHIM_H
#define AWS_CLI_NATIVE_CRT_SHIM_H
#include <aws/auth/credentials.h>
#include <aws/common/common.h>
#include <aws/http/request_response.h>
#include <aws/io/channel_bootstrap.h>
#include <aws/io/event_loop.h>
#include <aws/io/host_resolver.h>
#include <aws/io/tls_channel_handler.h>
#include <aws/s3/s3_buffer_pool.h>
#include <aws/s3/s3_client.h>
struct aws_allocator *rust_crt_allocator(void);
void rust_crt_library_init(struct aws_allocator *);
void rust_crt_library_clean_up(void);
struct aws_event_loop_group *rust_crt_event_loop_new(struct aws_allocator *,uint16_t,aws_simple_completion_callback *,void *);
struct aws_host_resolver *rust_crt_resolver_new(struct aws_allocator *,struct aws_event_loop_group *,aws_simple_completion_callback *,void *);
struct aws_client_bootstrap *rust_crt_bootstrap_new(struct aws_allocator *,struct aws_event_loop_group *,struct aws_host_resolver *,aws_simple_completion_callback *,void *);
int rust_crt_last_error(void);
const char *rust_crt_error_name(int);
const char *rust_crt_error_message(int);
#endif
