/*******************************************************************************
    Copyright (c) The Taichi Authors (2016- ). All Rights Reserved.
    The use of this software is governed by the LICENSE file.
*******************************************************************************/

// Modified by Infernux: bit tests live in tests/infernux, not the runtime library.
#include "taichi/util/bit.h"

namespace taichi {

namespace bit {

Bitset::Bitset() {
}

Bitset::Bitset(int n) {
  if (n % kBits != 0) {
    n += kBits - n % kBits;
  }
  vec_ = std::vector<value_t>(n / kBits, 0);
}

std::size_t Bitset::size() const {
  return vec_.size() * kBits;
}

void Bitset::reset() {
  for (auto &value : vec_) {
    value = 0;
  }
}

void Bitset::flip(int x) {
  vec_[x / kBits] ^= ((value_t)1) << (x % kBits);
}

bool Bitset::any() const {
  for (auto &val : vec_) {
    if (val)
      return true;
  }
  return false;
}

bool Bitset::none() const {
  return !any();
}

Bitset::reference Bitset::operator[](int x) {
  return reference(vec_, x);
}

Bitset &Bitset::operator&=(const Bitset &other) {
  const int len = vec_.size();
  TI_ASSERT(len == other.vec_.size());
  for (int i = 0; i < len; i++) {
    vec_[i] &= other.vec_[i];
  }
  return *this;
}

Bitset Bitset::operator&(const Bitset &other) const {
  Bitset result = *this;
  result &= other;
  return result;
}

Bitset &Bitset::operator|=(const Bitset &other) {
  const int len = vec_.size();
  TI_ASSERT(len == other.vec_.size());
  for (int i = 0; i < len; i++) {
    vec_[i] |= other.vec_[i];
  }
  return *this;
}

Bitset Bitset::operator|(const Bitset &other) const {
  Bitset result = *this;
  result |= other;
  return result;
}

Bitset &Bitset::operator^=(const Bitset &other) {
  const int len = vec_.size();
  TI_ASSERT(len == other.vec_.size());
  for (int i = 0; i < len; i++) {
    vec_[i] ^= other.vec_[i];
  }
  return *this;
}

Bitset Bitset::operator~() const {
  Bitset result(size());
  const int len = vec_.size();
  for (int i = 0; i < len; i++) {
    result.vec_[i] = ~vec_[i];
  }
  return result;
}

int Bitset::find_first_one() const {
  return lower_bound(0);
}

int Bitset::lower_bound(int x) const {
  const int len = vec_.size();
  if (x >= len * kBits) {
    return -1;
  }
  if (x < 0) {
    x = 0;
  }
  int i = x / kBits;
  if (x % kBits != 0) {
    if (auto test = vec_[i] & (kMask ^ ((1ULL << (x % kBits)) - 1))) {
      return i * kBits + log2int(lowbit(test));
    }
    i++;
  }
  for (; i < len; i++) {
    if (vec_[i]) {
      return i * kBits + log2int(lowbit(vec_[i]));
    }
  }
  return -1;
}

std::vector<int> Bitset::or_eq_get_update_list(const Bitset &other) {
  const int len = vec_.size();
  TI_ASSERT(len == other.vec_.size());
  std::vector<int> result;
  for (int i = 0; i < len; i++) {
    auto update = other.vec_[i] & ~vec_[i];
    if (update) {
      vec_[i] |= update;
      for (int j = 0; j < kBits; j++) {
        if ((update >> j) & 1) {
          result.push_back((i * kBits) | j);
        }
      }
    }
  }
  return result;
}

Bitset::reference::reference(std::vector<value_t> &vec, int x)
    : pos_(&vec[x / kBits]), digit_(((value_t)1) << (x % kBits)) {
}

Bitset::reference::operator bool() const {
  return *pos_ & digit_;
}

bool Bitset::reference::operator~() const {
  return ~*pos_ & digit_;
}

Bitset::reference &Bitset::reference::operator=(bool x) {
  if (x)
    *pos_ |= digit_;
  else
    *pos_ &= kMask ^ digit_;
  return *this;
}

Bitset::reference &Bitset::reference::operator=(
    const Bitset::reference &other) {
  *this = bool(other);
  return *this;
}

Bitset::reference &Bitset::reference::flip() {
  *pos_ ^= digit_;
  return *this;
}

std::ostream &operator<<(std::ostream &os, const Bitset &b) {
  for (auto &val : b.vec_)
    for (int j = 0; j < Bitset::kBits; j++)
      os << ((val >> j) & 1 ? '1' : '0');
  return os;
}

}  // namespace bit


}  // namespace taichi
