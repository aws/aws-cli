#include <aws/s3/s3.h>
#include <aws/common/allocator.h>

int main(void) {
    aws_s3_library_init(aws_default_allocator());
    aws_s3_library_clean_up();
    return 0;
}
