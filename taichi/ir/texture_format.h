#pragma once
// Modified by Infernux: texture formats are compiler metadata, not device APIs.
#include <cstdint>

namespace taichi::lang {

enum class BufferFormat : uint32_t {
#define PER_BUFFER_FORMAT(x) x,
#include "taichi/inc/rhi_constants.inc.h"
#undef PER_BUFFER_FORMAT
};

}  // namespace taichi::lang
