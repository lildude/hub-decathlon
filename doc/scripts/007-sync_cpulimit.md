# sync_cpulimit.py

Ce script a pour but de limiter le nombre de CPU utilisé par les différents process de synchronisation
Ce script est en exécution permanente, c'est à dire qu'il ne s'arrêtera pas de tourner tant qu'il n'y aura pas de plantage, ni d'intervention humaine pour l'arrêter.
Il utilise les modules tapiriik, pymongo et kombu.

### Déroulement du script : 
- Récupération du nombre limit de CPU utilisable, enregistré dans le fichier de configuration
- Toutes les secondes (+ temps de traitement de la procédure suivante)
```
time.sleep(1)
```
- Récupération des process ID fonctionnels ainsi que de leurs commandes
- Si la commande exécutée pour activer le process comprend le fichier "sync.worker.py" et que si le process ID de celui-ci indique qu'il est terminé
```
if pid not in cpulimit_procs or cpulimit_procs[pid].poll():
```
- On ouvre un sous-process
```
cpulimit_procs[pid] = subprocess.Popen(["cpulimit", "-l", str(worker_cpu_limit), "-p", pid])
```
- Ensuite, pour tous les process ID contenus dans la liste des cpulimit process ID
- Si l'un d'eux est identifié comme non terminé, on attend la fin de celui-ci
- Puis on le supprime de la liste des process cpulimit 
```
if cpulimit_procs[k].poll():
    cpulimit_procs[k].wait()
    del cpulimit_procs[k]
```

# [Back to script summary](000-script-summary.md)
