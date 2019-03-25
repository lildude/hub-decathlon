# sync_cpulimit.py

This script aims to limit the number of CPUs used by the different synchronization processes.
This script is in permanent execution, that is to say it will not stop turning as long as there will be no crash, nor human intervention to stop it.
It uses tapiriif, pymongo and kombu modules.

### Script flow : 
- Getting CPU limit, stored in conf file
- Every second (+ treatment time of next lines)
```
time.sleep(1)
```
- Getting current process ID with their "launch commands"
- If executed command contains "sync_worker.py" and if its process ID is tag as "ended"
```
if pid not in cpulimit_procs or cpulimit_procs[pid].poll():
```
- Open new sub-process
```
cpulimit_procs[pid] = subprocess.Popen(["cpulimit", "-l", str(worker_cpu_limit), "-p", pid])
```
- For each process ID in cpulimit list
- If one of them is identified as "not end", we wait the end of the process 
- Then delete it from cpulimit list
```
if cpulimit_procs[k].poll():
    cpulimit_procs[k].wait()
    del cpulimit_procs[k]
```

# [Back to script summary](000-script-summary.md)
