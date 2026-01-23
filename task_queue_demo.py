import task_queue as tq

N = 100
# data = [1]*N
data = list(range(N))
def stage_a_fn(i):
    data[i]*=2

def stage_b_fn(i):
    data[i]+=1

def stage_c_fn(i):
    print("final:",i, data[i])

stage_a = tq.Stage("A", 2, 8, stage_a_fn)
stage_b = tq.Stage("B", 2, 8, stage_b_fn)
stage_c = tq.Stage("C", 2, 8, stage_c_fn)

tq.chain(stage_a, stage_b)
tq.chain(stage_b, stage_c)


stage_a.setTaskCount(N)
stage_b.setTaskCount(N)
stage_c.setTaskCount(N)


for i in range(N):
    stage_a.push(i)

stage_c.pool.wait()
