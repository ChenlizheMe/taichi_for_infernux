#pragma once

#include "taichi/common/logging.h"
#include "taichi/common/core.h"

#include "public_device.h"

// Modified by Infernux: formatting is internal to the logging-aware header.
template <>
class fmt::formatter<taichi::lang::RhiResult> {
 public:
  constexpr auto parse(format_parse_context &ctx) {
    return ctx.begin();
  }
  template <typename Context>
  constexpr auto format(taichi::lang::RhiResult const &res,
                        Context &ctx) const {
    return format_to(ctx.out(), taichi::lang::rhi_result_to_string(res));
  }
};
