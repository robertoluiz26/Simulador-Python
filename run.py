import argparse
import copy
import pickle
import datetime
import time
import shutil
import sys
import git
import os
import numpy as np
from multiprocessing import Pool
from multiprocessing import Manager

import core
import graph
import plots
import routing_policies
import restoration_policies

import logging
logging.basicConfig(format='%(asctime)s\t%(name)-12s\t%(threadName)s\t%(message)s', level=logging.DEBUG)


def run(uargs):
    start_time = time.time()

    topology = graph.get_topology(uargs)
    topology = graph.get_dcs(uargs, topology)
    topology = graph.get_ksp(uargs, topology)
    topology = graph.get_probability_ksp(uargs, topology)    
    env = core.Environment(uargs, topology=topology)

    logger = logging.getLogger('run')

    # in this case, a configuration changes only the load of the network
    # 'RADC', 'FADC', 'FLB'
    exec_routing_policies = ['CADC']
    #'PR','DNR','PRCA'
    #exec_restoration_policies = ['PRPA','PRwR','PRPA(α=1)','PRPA(α=0.5)','PRPA(α=0.7)','PRPA(α=0.9)'] #,'ILP']
    #exec_restoration_policies = ['PRPA(α=0.5)','ILP']
    #exec_restoration_policies = ['ILP', 'ILP_PRwR', 'ILP_HC']
    exec_restoration_policies = ['PRPA(α=0.0)']
    #exec_restoration_policies = ['PRwR','PRPA(α=0.5)']
    #exec_restoration_policies = ['ILP', 'ILP_PRwR', 'ILP_HC','PRwR','PRPA(α=1)','PRPA(α=0.5)','PRPA(α=0.4)','PRPA(α=0.3)','PRPA(α=0.1)']
    #exec_restoration_policies = ['PRPA(α=0.1)', 'PRPA(α=0.5)', 'ILP']
    #exec_restoration_policies = ['PRPA(α=0.1)']
    #exec_restoration_policies = ['ILP','PRwR','PRPA(α=1)','PRPA(α=0.5)','PRPA(α=0.4)','PRPA(α=0.3)','PRPA(α=0.1)']
    loads = [x for x in range(args.min_load, args.max_load + 1, args.load_step)]
    #loads = [x for x in range(args.min_load, args.min_load + 1, args.load_step)]

    final_output_folder = env.output_folder + '/' + datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fUTC')
    env.output_folder = final_output_folder

    if not os.path.isdir('./results/' + env.output_folder):
        os.makedirs('./results/' + env.output_folder)
        logger.debug(f'creating folder {env.output_folder}')
    
    # creating a graphical representation of the topology
    plots.plot_topology(env, args)

    # copy current version of files
    with open('./results/{}/0-info.txt'.format(env.output_folder), 'wt') as file:
        width = 20
        print('Date (UTC):'.ljust(width), datetime.datetime.now(datetime.timezone.utc), file=file)
        print('Date (local):'.ljust(width), datetime.datetime.now(), file=file)
        # repo = git.Repo()
        # print('Commit date:'.ljust(width),
        #       datetime.datetime.fromtimestamp(repo.head.object.committed_date).strftime('%Y-%m-%d %H:%M:%S'),
        #       file=file)
        # print('Author:'.ljust(width), repo.head.object.committer, file=file)
        # print('GIT hexsha:'.ljust(width), repo.head.object.hexsha, file=file)
        print('Command:'.ljust(width), ' '.join(sys.argv), file=file)
        print('Arguments:'.ljust(width), args, file=file)

    # copy current version of files
    shutil.copytree('./', f'./results/{env.output_folder}/source-code/',
                    ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '*.md', 'results', 'LICENSE', '*.ipynb', '.git', '.idea', '.gitignore'))

    # preparing the thread-safe data structure to hold the results
    manager = Manager()
    results = manager.dict()
    for routing_policy in exec_routing_policies:
        results[routing_policy] = manager.dict()
        for restoration_policy in exec_restoration_policies:
            results[routing_policy][restoration_policy] = {load: manager.list() for load in loads}
    
    envs = []
    cont = 0
    cont_1 = 0
    cont_2 = 0
    cont_3 = 0
    for routing_policy in exec_routing_policies:  # runs the simulations for every routing policy
        for restoration_policy in exec_restoration_policies:  # runs the simulations for every restoration policy
            
            for load in loads:  # runs the simulations for every load

                if routing_policy == 'CADC':
                    routing_policy_instance = routing_policies.ClosestAvailableDC()
                #elif routing_policy == 'RADC':
                #    routing_policy_instance = routing_policies.RandomAvailableDC()
                #elif routing_policy == 'FLB':
                #    routing_policy_instance = routing_policies.FullLoadBalancing()
                else:
                    raise ValueError('Routing policy was not configured correctly (value set to {})'.format(routing_policy))

                #if restoration_policy == 'DNR':
                #    restoration_policy_instance = restoration_policies.DoNotRestorePolicy()
                #if restoration_policy == 'PR':
                #    restoration_policy_instance = restoration_policies.PathRestorationPolicy()
                if restoration_policy == 'PRwR':
                    restoration_policy_instance = restoration_policies.PathRestorationWithRelocationPolicy()
                elif restoration_policy == 'PRPA(α=1)':
                    restoration_policy_instance = restoration_policies.PathRestorationPropabilitiesAware()
                elif restoration_policy == 'PRPA(α=0.5)':
                    restoration_policy_instance = restoration_policies.PathRestorationBalancedPropabilitiesAware()
                elif restoration_policy == 'PRPA(α=0.4)':
                    restoration_policy_instance = restoration_policies.PathRestorationBalancedPropabilitiesAware04()
                elif restoration_policy == 'PRPA(α=0.3)':
                    restoration_policy_instance = restoration_policies.PathRestorationBalancedPropabilitiesAware03()
                elif restoration_policy == 'PRPA(α=0.1)':
                    restoration_policy_instance = restoration_policies.PathRestorationBalancedPropabilitiesAware01()
                elif restoration_policy == 'PRPA(α=0.0)':
                    restoration_policy_instance = restoration_policies.PathRestorationBalancedPropabilitiesAware00()
                elif restoration_policy == 'ILP':
                    restoration_policy_instance = restoration_policies.ILP_probability_awareness(cont)
                    cont+=1
                elif restoration_policy == 'ILP_PRwR':
                    restoration_policy_instance = restoration_policies.ILP_without_probability_awareness(cont_1)
                    cont_1+=1
                elif restoration_policy == 'ILP_HC':
                    restoration_policy_instance = restoration_policies.ILP_probability_awareness_with_higher_cost(cont_2)
                    cont_2+=1
                elif restoration_policy == 'ILP_whut':
                    restoration_policy_instance = restoration_policies.ILP_probability_awareness_with_higher_ut(cont_3)
                    cont_3+=1
                else:
                    raise ValueError('Restoration policy was not configured correctly (value set to {})'.format(restoration_policy))

                env_topology = copy.deepcopy(topology) # makes a deep copy of the topology object
                env_t = core.Environment(uargs,
                                        topology=env_topology,
                                        results=results,
                                        load=load,
                                        routing_policy=routing_policy_instance,
                                        restoration_policy=restoration_policy_instance,
                                        seed=len(exec_routing_policies) * load,
                                        output_folder=env.output_folder)
                envs.append(env_t)
                # code for debugging purposes -- it runs without multithreading
                
                # if load == 600 and routing_policy == 'CADC':
                
                ''' 
                core.run_simulation(env_t)
                print("Ran in debug mode... exiting...")
                exit(0)
                '''
    logger.debug(f'Starting pool of simulators with {uargs.threads} threads')
    # use the code above to keep updating the final plot as the simulation progresses
    with Pool(processes=uargs.threads) as p:
        result_pool = p.map_async(core.run_simulation, envs)
        p.close()

        done = False
        while not done:
            if result_pool.ready():
                done = True
            else:
                time.sleep(uargs.temporary_plot_every)
                plots.plot_final_results(env, results, start_time)

    # if you do not want periodical updates, you can use the following code
    # with Pool(processes=uargs.threads) as p:
    #     p.map(core.run_simulation, envs)
    #     p.close()
    #     p.join()
    #     logging.debug("Finished the threads")

    # consolidating statistics
    plots.plot_final_results(env, results, start_time)

    with open('./results/{}/final_results.h5'.format(env.output_folder), 'wb') as file:
        realized_results = dict(results)
        for k1, v1 in results.items():
            realized_results[k1] = dict(v1)
            for k2, v2 in results[k1].items():
                realized_results[k1][k2] = dict(v2)
                for k3, v3 in results[k1][k2].items():
                    realized_results[k1][k2][k3] = list(v3)
        pickle.dump({
            'args': uargs,
            'env': env,
            'results': realized_results,
            'routing_policies': [policy for policy in exec_routing_policies],
            'restoration_policies': [policy for policy in exec_restoration_policies],
            'loads': loads,
            'timedelta': datetime.timedelta(seconds=(time.time() - start_time)),
            'datetime': datetime.datetime.fromtimestamp(time.time())
        }, file)

    logger.debug('Finishing simulation after {}'.format(datetime.timedelta(seconds=(time.time() - start_time))))


if __name__ == '__main__':
    env = core.Environment()

    parser = argparse.ArgumentParser()
    parser.add_argument('--plot_simulation_progress', default=False, action='store_true',
                        help='Plot summary for each seed simulated (default=False)')
    parser.add_argument('-tf', '--topology_file', default=env.topology_file, help='Network topology file to be used')
    parser.add_argument('-a', '--num_arrivals', type=int, default=env.num_arrivals,
                        help='Number of arrivals per episode to be generated (default={})'.format(env.num_arrivals))
    parser.add_argument('-k', '--k_paths', type=int, default=env.k_paths,
                        help='Number of k-shortest-paths to be considered (default={})'.format(env.k_paths))
    parser.add_argument('-d', '--num_dcs', type=int, default=env.num_dcs,
                        help='Number of datacenters to be placed (default={})'.format(env.num_dcs))
    parser.add_argument('--dc_placement', default=env.dc_placement,
                        help='DC placement criteria (default={})'.format(env.dc_placement))
    parser.add_argument('-t', '--threads', type=int, default=env.threads,
                        help='Number of threads to be used to run the simulations (default={})'.format(
                            env.threads))
    parser.add_argument('--min_load', type=int, default=560,
                        help='Load in Erlangs of the traffic generated (mandatory)')
    parser.add_argument('--max_load', type=int, default=840,
                        help='Load in Erlangs of the traffic generated (mandatory)')
    parser.add_argument('--load_step', type=int, default=40,
                        help='Load in Erlangs of the traffic generated (default: {})'.format(50))
    parser.add_argument('-s', '--seed', type=int, default=env.seed,
                        help='Seed of the random numbers (default={})'.format(env.seed))
    parser.add_argument('-ns', '--num_seeds', type=int, default=env.num_seeds,
                        help='Number of seeds to run for each configuration (default={})'.format(env.num_seeds))
    te = 5
    parser.add_argument('-te', '--temporary_plot_every', type=int, default=te, #TODO: adjust for your needs
                        help='Time interval for plotting intermediate statistics of the simulation in seconds (default={})'.format(te))
    parser.add_argument('-o', '--output_folder', default=env.output_folder,
                        help='Output folder inside results (default={})'.format(env.output_folder))
    parser.add_argument('-do', '--disaster_occurences', default=env.number_disaster_occurences,
                        help='Number of disasters to occur for each seed simulated'.format(env.number_disaster_occurences))
    parser.add_argument('-fd', '--failure_duration', default=env.mean_failure_duration,
                        help='Mean failure or disaster duration'.format(env.mean_failure_duration))
    args = parser.parse_args()
    run(args)
