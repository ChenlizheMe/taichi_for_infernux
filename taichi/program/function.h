#pragma once

#include <unordered_set>
#include "taichi/program/callable.h"
#include "taichi/program/function_key.h"

namespace taichi::lang {

class Program;
class Stmt;

class Function : public Callable {
 public:
  enum class IRStage : int {
    None = 0,
    AST = 1,
    InitialIR = 2,
    BeforeLowerAccess = 3,
    OptimizedIR = 4
  };

  FunctionKey func_key;

  Function(Program *program, const FunctionKey &func_key);

  // Set the function body to a frontend Python function which generates the C++
  // AST.
  void set_function_body(const std::function<void()> &func);

  // Set the function body to a CHI IR.
  void set_function_body(std::unique_ptr<IRNode> func_body);

  [[nodiscard]] std::string get_name() const override;

  void set_ir_stage(IRStage type) {
    ir_stage_ = type;
  }

  IRStage ir_stage() const {
    return ir_stage_;
  }

  std::unordered_set<Stmt *> store_dests;

 private:
  IRStage ir_stage_{IRStage::None};
};

}  // namespace taichi::lang
