#include "task_queue.hpp"

#include <algorithm>
#include <future>
#include <numeric>
#include <stdio.h>

int main1()
{
    int N = 100;

    ThreadPoolEx<BoundedTaskQueue> a(2), b(2), c(2);
    a.taskQueue.setCapacity(8);
    b.taskQueue.setCapacity(8);
    c.taskQueue.setCapacity(8);
    a.setTaskCount(N);
    b.setTaskCount(N);
    c.setTaskCount(N);

    std::vector<int> datas(N, 0);
    std::iota(datas.begin(), datas.end(), 0);
    std::future<void> future = std::async(std::launch::async, [&]() {
        for (int i = 0; i < N; ++i) {
            a.pushTask([&, i]() -> void {
                datas[i] *= 2;
                b.pushTask([&, i]() -> void {
                    datas[i] += 1;
                    c.pushTask([&, i]() -> void {
                        printf("%d,%d\n", i, datas[i]);
                    });
                });
            });
        }
    });

    c.wait();

    return 0;
}

int main2()
{
    int N = 100;

    std::vector<int> datas(N, 0);
    std::iota(datas.begin(), datas.end(), 0);

    Stage stageA("A", 2, 8, [&](int i) {
        datas[i] *= 2;
    });

    Stage stageB("B", 2, 8, [&](int i) {
        datas[i] += 1;
    });

    Stage stageC("C", 2, 4, [&](int i) {
        printf("%d,%d\n", i, datas[i]);
    });
    chain(stageA, stageB);
    chain(stageB, stageC);
    stageA.setTaskCount(N);
    stageB.setTaskCount(N);
    stageC.setTaskCount(N);

    // 在另一个线程中push任务，主线程可以继续做其他事情
    std::future<void> future = std::async(std::launch::async, [&]() {
        for (int i = 0; i < N; ++i) {
            stageA.push(i);
        }
    });

    // 主线程可以同时做其他工作
    printf("主线程可以同时处理其他任务...\n");
    for (int i = 0; i < 5; ++i) {
        printf("主线程正在处理其他工作 %d/5\n", i + 1);
        std::this_thread::sleep_for(std::chrono::milliseconds(50));
    }
    printf("主线程完成其他工作\n");

    // 等待流水线处理完成
    printf("等待流水线处理完成...\n");
    stageC.wait();
    printf("所有任务处理完成\n");

    return 0;
}

int main()
{
    main1();
    main2();
    return 0;
}