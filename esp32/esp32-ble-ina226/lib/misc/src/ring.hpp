
#pragma once

#include <atomic>
#include <cstddef>

template <typename T, size_t Size>
class RingBuffer {
    static_assert((Size & (Size - 1)) == 0, "Size must be a power of 2");

private:
    T buffer[Size];
    std::atomic<size_t> head{0};  // Producer index (Interrupt context)
    std::atomic<size_t> tail{0};  // Consumer index (User context)

public:
    bool push(const T item) {
        size_t headIdx = head.load(std::memory_order_relaxed);
        size_t nextHead = (headIdx + 1) & (Size - 1);

        if (nextHead == tail.load(std::memory_order_acquire)) {
            return false;  // Buffer full
        }

        buffer[headIdx] = item;
        head.store(nextHead, std::memory_order_release);
        return true;
    }

    T pop() {
        size_t tailIdx = tail.load(std::memory_order_relaxed);

        while (tailIdx == head.load(std::memory_order_acquire)) {
            // Buffer empty
        }

        T item = buffer[tailIdx];
        tail.store((tailIdx + 1) & (Size - 1), std::memory_order_release);
        return item;
    }
};
