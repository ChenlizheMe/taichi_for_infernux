# Taichi for Infernux

[English](README.md) · [Infernux 引擎](https://github.com/ChenlizheMe/Infernux) · [Taichi 上游](https://github.com/taichi-dev/taichi)

这是为 **Infernux 游戏引擎**维护的 Taichi 编译器分支。Infernux 使用 C++ 实现底层，使用 Python 编写游戏逻辑。这里的编译模块将随引擎本体 wheel 分发，**不是项目插件**，游戏作者不需要另外安装 Taichi。

## 我们保留什么

当前只做 JIT：将引擎的数值计算代码编译成 Vulkan 使用的 SPIR-V，并给出参数与资源绑定信息。GPU buffer、设备、显存、提交、同步和释放都由 Infernux 管理，不再由这个分支维护 `taichi.field`、SNode 存储或独立 Vulkan 运行时。

CPU 计算继续使用引擎的 Numba/llvmlite 路径；引擎和适用的 Player 构建将同时携带 CPU、GPU 两套 JIT 工具。AOT 导出及独立 AOT 运行库暂不纳入交付。

## 当前进度

裁剪和发行集成仍在进行中。引擎构建已经能将私有 Python 前端和原生 SPIR-V 编译模块直接安装到 wheel 目录；Windows 集成测试覆盖无 GPU 设备的内核编译，以及通过 Infernux Vulkan 后端执行编译结果。

当前使用的 Python 前端已移除 field/SNode 存储管理、设备数组构造和内核执行运行时。导入限定在 `Infernux._compiler.taichi` 内部，不占用公共 `taichi` 包名；矩阵、向量数值表达式和代码生成所需的 IR 继续保留。

独立 C-API、AOT 模块构建/加载器、CPU/LLVM/CUDA/AMDGPU/DirectX 代码生成与执行运行时、上游设备后端及旧数据容器，现已从源码删除，而非仅关闭选项。Python AOT/Graph 导出工具、Field 树构建器、自动微分作者入口及独立 Taichi 命令行也已移除。SPIR-V 编译器保留共享 IR 和能力/格式描述，不再带另一套 GPU 设备实现。共享 IR、旧 UI/工具和历史测试仍需继续裁剪；完整的多平台 wheel 与 Player 发行矩阵尚未验收。

编译直接读取引擎提供的 buffer 类型描述，不再分配 NumPy 占位数组。每个入口只创建一个正向内核，自动梯度内核和类方法探测已移除。引擎的 `infernux.compute_compiler_only` 正式测试会从安装后的编译器生成 SPIR-V，不加载引擎，也不创建 GPU 设备；实际执行另由 Vulkan 集成测试覆盖。

辅助函数统一内联到 kernel，不再维护另一套独立函数的编译、调用和缓存接口。优化器所需的共享 IR 仍保留在编译器内部。

编译内核自行持有原生 IR，并在需要时保持编译上下文存活。Python 和 Program 不再长期登记每个编译过的内核；引擎保留的是导出的 SPIR-V 制品，不是已用完的编译对象或临时生成源码。

原生上下文直接调用 SPIR-V 编译器，不再经过可切换后端接口，也不再限制整个进程只能有一个上下文。输出只包含代码与元数据；旧 TIC 文件序列化、内容哈希和执行句柄已移除，制品缓存继续由引擎负责。这不代表共享 Python 前端和类型工厂已经支持并发编译。

编译所需的纹理格式、设备能力描述已与设备操作接口分开。旧的显存分配、上传回读和命令提交实现及其构建目标已删除，这些操作只由 Infernux 执行。

引擎侧已经接入 `inx.buffer`、`set_data/get_data`、小写 `inx.vector3`，并将 CPU `@inx.jit.compile` 与 GPU `@inx.compute.kernel`、`inx.compute.launch` 分开。这些是 Infernux 的接口，不是本仓库提供的独立 Taichi 作者 API。

## 构建与分发

统一通过 CMake 和引擎的 `infernux_gpu_jit_compiler` 目标构建，不再保留独立 `setup.py`/Taichi wheel 发布入口。集成测试使用 `INFERNUX_BUILD_TESTS`，不再支持旧的上游运行时测试目标。

引擎开发使用 `infernux` conda 环境。源码依赖位于 `external/taichi_for_infernux`，不再放入 `external/plugins`。

`infernux-jit` CMake preset 禁用 AOT C-API 和不需要的后端。原生绑定直接输出到 `build/infernux-jit/wheel/Infernux/_compiler/taichi/_vendor/taichi/_lib/core`，也可以用 `INFERNUX_COMPILER_OUTPUT_DIR` 指定引擎自己的原生编译模块输出目录。

`infernux_compiler` 安装组件负责原生绑定、私有 Python 前端以及 LICENSE/NOTICE。引擎的 `infernux_gpu_jit_compiler` 目标完成构建和安装，不需要手动搬运。跨平台依赖收集及 Player 的双 JIT 打包仍需完成。不再以 `.inxpkg` 或独立 Taichi wheel 为交付目标，上游遗留发布脚本也不是 Infernux 的发布入口。

当前 CI 在 Windows/Linux 检查构建配置，并实际构建一个小型原生测试库，将私有前端和 LICENSE/NOTICE 安装到预期目录。这验证的是 wheel 目录与载荷交付，不代替完整编译器构建、运行正确性或性能验收。

## 来源与许可

感谢 [Taichi](https://github.com/taichi-dev/taichi) 原作者及所有贡献者。源码保留原有版权和署名，见 [LICENSE](LICENSE) 和 [NOTICE](NOTICE)。这是 Infernux 维护的分支，不是 Taichi 官方发行版。
