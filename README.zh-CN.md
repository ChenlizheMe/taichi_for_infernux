# Taichi for Infernux

[English](README.md) · [Infernux 引擎](https://github.com/ChenlizheMe/Infernux) · [Taichi 上游](https://github.com/taichi-dev/taichi)

这是为 **Infernux 游戏引擎**维护的 Taichi 编译器分支。Infernux 使用 C++ 实现底层，使用 Python 编写游戏逻辑。这里的编译模块将随引擎本体 wheel 分发，**不是项目插件**，游戏作者不需要另外安装 Taichi。

## 我们保留什么

当前只做 JIT：将引擎的数值计算代码编译成 Vulkan 使用的 SPIR-V，并给出参数与资源绑定信息。GPU buffer、设备、显存、提交、同步和释放都由 Infernux 管理，不再由这个分支维护 `taichi.field`、SNode 存储或独立 Vulkan 运行时。

CPU 计算继续使用引擎的 Numba/llvmlite 路径；引擎和适用的 Player 构建将同时携带 CPU、GPU 两套 JIT 工具。AOT 导出及独立 AOT 运行库暂不纳入交付。

## 当前进度

裁剪和集成仍在进行中。仓库先明确新的定位、JIT 构建约束和原生模块输出位置，**还不是可以直接使用的完整制品**。源码仍有待拆除的上游运行时和 AOT 实现，关闭选项不等于已经删干净；本地引擎实验也尚未全部发布。

新的作者接口计划使用 `inx.buffer`、`set_data/get_data`、小写 `inx.vector3`，并将 CPU `@inx.jit.compile` 与 GPU `@inx.compute.kernel`、`inx.compute.launch` 分开。这些是迁移目标，不是当前版本的运行示例。

## 构建与分发

引擎开发使用 `infernux` conda 环境。源码依赖位于 `external/taichi_for_infernux`，不再放入 `external/plugins`。

`infernux-jit` CMake preset 禁用 AOT C-API 和不需要的后端。原生绑定直接输出到 `build/infernux-jit/wheel/Infernux/_compiler/taichi`，也可以用 `INFERNUX_COMPILER_OUTPUT_DIR` 指定引擎自己的 wheel staging 目录。

`infernux_compiler` 安装组件负责原生模块和许可文件。前端依赖收集、完整 wheel 与 Player 的双 JIT 打包仍需接通。不再以 `.inxpkg` 或独立 Taichi wheel 为交付目标，上游遗留发布脚本也不是 Infernux 的发布入口。

当前 CI 在 Windows/Linux 检查构建配置和输出合同；实际编译、运行与性能验收仍需完成，不能用配置检查通过代替。

## 来源与许可

感谢 [Taichi](https://github.com/taichi-dev/taichi) 原作者及所有贡献者。源码保留原有版权和署名，见 [LICENSE](LICENSE) 和 [NOTICE](NOTICE)。这是 Infernux 维护的分支，不是 Taichi 官方发行版。
