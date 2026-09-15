#include "taichi/program/kernel.h"

#include "taichi/common/logging.h"
#include "taichi/common/task.h"
#include "taichi/ir/statements.h"
#include "taichi/program/program.h"

namespace taichi::lang {

class Function;

Kernel::Kernel(Program &program,
               const std::function<void()> &func,
               const std::string &primal_name,
               AutodiffMode autodiff_mode) {
  this->init(program, func, primal_name, autodiff_mode);
}

Kernel::Kernel(Program &program,
               const std::function<void(Kernel *)> &func,
               const std::string &primal_name,
               AutodiffMode autodiff_mode) {
  // due to #6362, we cannot write [func, this] { return func(this); }
  this->init(program, [&] { return func(this); }, primal_name, autodiff_mode);
}

Kernel::Kernel(Program &program,
               std::unique_ptr<IRNode> &&ir,
               const std::string &primal_name,
               AutodiffMode autodiff_mode) {
  this->arch = program.compile_config().arch;
  this->autodiff_mode = autodiff_mode;
  this->ir = std::move(ir);
  this->program = &program;
  is_accessor = false;
  ir_is_ast_ = false;  // CHI IR

  TI_ASSERT(this->ir->is<Block>());
  this->ir->as<Block>()->set_parent_callable(this);

  if (autodiff_mode == AutodiffMode::kNone) {
    name = primal_name;
  } else if (autodiff_mode == AutodiffMode::kForward) {
    name = primal_name + "_forward_grad";
  } else if (autodiff_mode == AutodiffMode::kReverse) {
    name = primal_name + "_reverse_grad";
  } else if (autodiff_mode == AutodiffMode::kCheckAutodiffValid) {
    name = primal_name + "_validate_grad";
  } else {
    TI_ERROR("Unsupported autodiff mode");
  }
}

std::string Kernel::get_name() const {
  return name;
}

void Kernel::init(Program &program,
                  const std::function<void()> &func,
                  const std::string &primal_name,
                  AutodiffMode autodiff_mode) {
  this->autodiff_mode = autodiff_mode;
  this->program = &program;

  is_accessor = false;
  context = std::make_unique<FrontendContext>(program.compile_config().arch,
                                              /*is_kernel_=*/true);
  ir = context->get_root();

  TI_ASSERT(ir->is<Block>());
  ir->as<Block>()->set_parent_callable(this);

  ir_is_ast_ = true;
  arch = program.compile_config().arch;

  if (autodiff_mode == AutodiffMode::kNone) {
    name = primal_name;
  } else if (autodiff_mode == AutodiffMode::kCheckAutodiffValid) {
    name = primal_name + "_validate_grad";
  } else if (autodiff_mode == AutodiffMode::kForward) {
    name = primal_name + "_forward_grad";
  } else if (autodiff_mode == AutodiffMode::kReverse) {
    name = primal_name + "_reverse_grad";
  }

  func();
}
}  // namespace taichi::lang
