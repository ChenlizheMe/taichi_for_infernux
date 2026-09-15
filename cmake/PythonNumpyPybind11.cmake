# Modified by the Infernux project in 2026: one Python interpreter/ABI
# contract, using FindPython instead of removed legacy discovery modules.
# The root build selects the interpreter and module ABI once, including the
# interpreter used to generate SPIR-V tables in non-extension builds.
set(PYBIND11_FINDPYTHON ON)
execute_process(COMMAND "${Python_EXECUTABLE}" -m pybind11 --cmakedir
                OUTPUT_VARIABLE pybind11_DIR OUTPUT_STRIP_TRAILING_WHITESPACE
                COMMAND_ERROR_IS_FATAL ANY)
find_package(pybind11 3 CONFIG REQUIRED)
include_directories(${Python_NumPy_INCLUDE_DIRS})
