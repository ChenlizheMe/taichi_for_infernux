// Moved from upstream taichi/util/bit.cpp by Infernux in 2026.
// Copyright (c) The Taichi Authors (2016- ). See LICENSE.
// Keep compiler bit tests out of the shipped native module.
#include "taichi/util/bit.h"
#ifdef NDEBUG
#undef NDEBUG
#endif
#include <cassert>

using namespace taichi;
using namespace taichi::bit;

struct Flags : public Bits<32> {
  using Base = Bits<32>;
  TI_BIT_FIELD(bool, apple, 0);
  TI_BIT_FIELD(bool, banana, 1);
  TI_BIT_FIELD(uint8, cherry, 2);
};

int main() {
  Bits<32> b;
  b.set<5>(1);
  assert(b.get() == 32);
  b.set<10, 8>(255);
  assert(b.get() == 255 * 1024 + 32);
  b.set<11, 1>(0);
  assert(b.get() == 255 * 1024 + 32 - 2048);
  b.set<11, 2>(3);
  assert(b.get() == 255 * 1024 + 32);
  b.set<11, 2>(0);
  assert(b.get() == 255 * 1024 + 32 - 2 * 3072);
  b.set<11, 2>(1);
  assert(b.get() == 255 * 1024 + 32 - 4096);

  Flags f;
  f.set_apple(true);
  assert(f.get_apple() == true);
  f.set_apple(false);
  assert(f.get_apple() == false);
  f.set_banana(true);
  assert(f.get_banana() == true);
  assert(f.get_apple() == false);
  f.set_apple(false);
  assert(f.get_apple() == false);
  f.set_apple(true);
  f.set_cherry(63);
  assert(f.get_cherry() == 63);
  f.set_banana(false);
  assert(f.get_cherry() == 63);

  struct Decomp {
    uint8 a, b, c, d;
  };

  uint32 v = 0xabcd1234;
  auto &dec = reinterpret_bits<Decomp>(v);
  assert(dec.a == 0x34);
  assert(dec.b == 0x12);
  assert(dec.c == 0xcd);
  assert(dec.d == 0xab);
  dec.d = 0xef;
  assert(v == 0xefcd1234);

  assert(reinterpret_bits<float32>(reinterpret_bits<uint32>(1.32_f32)) ==
        1.32_f32);

}
