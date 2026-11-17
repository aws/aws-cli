#include "crt_shim.h"
#include <aws/common/allocator.h>
#include <aws/common/error.h>
#include <aws/s3/s3.h>
enum { RESOLVER_CACHE_HOSTS_MAX = 8 };
void rust_crt_library_init(struct aws_allocator *allocator) { aws_s3_library_init(allocator); }
void rust_crt_library_clean_up(void) { aws_s3_library_clean_up(); }
struct aws_event_loop_group *rust_crt_event_loop_new(struct aws_allocator *allocator,uint16_t count,aws_simple_completion_callback *callback,void *data) {
    struct aws_shutdown_callback_options shutdown={ .shutdown_callback_fn=callback,.shutdown_callback_user_data=data };
    struct aws_event_loop_group_options options={ .loop_count=count,.type=AWS_EVENT_LOOP_PLATFORM_DEFAULT,.shutdown_options=&shutdown };
    return aws_event_loop_group_new(allocator,&options);
}
struct aws_host_resolver *rust_crt_resolver_new(struct aws_allocator *allocator,struct aws_event_loop_group *group,aws_simple_completion_callback *callback,void *data) {
    struct aws_shutdown_callback_options shutdown={ .shutdown_callback_fn=callback,.shutdown_callback_user_data=data };
    struct aws_host_resolver_default_options options={ .max_entries=RESOLVER_CACHE_HOSTS_MAX,.el_group=group,.shutdown_options=&shutdown };
    return aws_host_resolver_new_default(allocator,&options);
}
struct aws_client_bootstrap *rust_crt_bootstrap_new(struct aws_allocator *allocator,struct aws_event_loop_group *group,struct aws_host_resolver *resolver,aws_simple_completion_callback *callback,void *data) {
    struct aws_client_bootstrap_options options={ .event_loop_group=group,.host_resolver=resolver,.on_shutdown_complete=callback,.user_data=data };
    return aws_client_bootstrap_new(allocator,&options);
}
int rust_crt_last_error(void) { return aws_last_error(); }
const char *rust_crt_error_name(int code) { return aws_error_name(code); }
const char *rust_crt_error_message(int code) { return aws_error_str(code); }
