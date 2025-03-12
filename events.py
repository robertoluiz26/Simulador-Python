from typing import Sequence
import typing
import os
if typing.TYPE_CHECKING:  # avoid circular imports
    from core import Environment, Service, LinkFailure, DisasterFailure


def arrival(env: 'Environment', service: 'Service') -> None:
    # logging.debug('Processing arrival {} for policy {} load {} seed {}'
    #               .format(service.service_id, env.policy, env.load, env.seed))

    success, dc, path = env.routing_policy.route(service)
    if success:
        service.route = path
        env.provision_service(service)
    else:
        env.reject_service(service)

    env.setup_next_arrival()  # schedules next arrival

def departure(env: 'Environment', service: 'Service') -> None:
    # computing the service time that can be later used to compute availability
    service.service_time = env.current_time - service.arrival_time
    service.service_time = service.service_time - service.downtime 
    service.availability = service.service_time / service.holding_time
    env.release_path(service)


def link_failure_arrival(env: 'Environment', failure: 'LinkFailure') -> None:
    from core import Event
    
    # saving status
    env.tracked_results['link_failure_arrivals'].append(env.current_time)
    
    # put the link in a failed state
    env.topology[failure.link_to_fail[0]][failure.link_to_fail[1]]['failed'] = True

    # get the list of disrupted services
    services_disrupted: Sequence[Service] = []  # create an empty list
    services_disrupted_correct: Sequence[Service] = [] 
    # extend the list with the running services
    services_disrupted.extend(env.topology[failure.link_to_fail[0]][failure.link_to_fail[1]]['running_services'])
    """for service in services_disrupted_correct:
        print("entrou link_failure_arrival")
        if (service.holding_time + service.arrival_time - env.current_time) > 0:
            service.remaining_time = service.holding_time + service.arrival_time - env.current_time
            print("service remaining_time = " + str(service.remaining_time))
            arquivo = "log.txt"
            # Abre o arquivo (cria se não existir) e escreve a mensagem
            if os.path.exists(arquivo):
                # Abre o arquivo em modo de acréscimo ('append')
                with open(arquivo, 'a') as f:
                    f.write('service.remaining_time = .\n' + str(service.remaining_time))
            else:
                # Cria um novo arquivo e escreve a mensagem
                with open(arquivo, 'w') as f:
                    f.write('service.remaining_time = .\n' + str(service.remaining_time))
            services_disrupted.append(service)"""

    number_disrupted_services: int = len(services_disrupted)

    env.logger.debug(f'Failure arrived at time: {env.current_time}\tLink: {failure.link_to_fail}\tfor {number_disrupted_services} services')

    if len(services_disrupted) > 0:
        for service in services_disrupted:
            # release all resources used
            env.logger.debug(f'Releasing resources for service {service}')
            env.release_path(service)

            queue_size = len(env.events)
            env.remove_service_departure(service)
            if queue_size -1 != len(env.events):
                env.logger.critical('Event not removed!')

            # set it to a failed state
            service.failed = True
            service.relocated = False
        
        if len(env.topology[failure.link_to_fail[0]][failure.link_to_fail[1]]['running_services']) != 0:
            env.logger.critical('Not all services were removed')
        
        # call the restoration strategy
        services_disrupted = env.restoration_policy.restore(services_disrupted)

        number_lost_services: int = 0
        number_restored_services: int = 0
        number_relocated_services: int = 0
        
        for service in services_disrupted:
            if service.failed!=True:  # service could be restored
                number_restored_services += 1
            
                if service.relocated:
                    number_relocated_services+=1

            else:
                number_lost_services += 1

        # register statistics such as restorability
        if number_disrupted_services > 0:
            restorability = number_restored_services / number_disrupted_services
            env.logger.debug(f'Failure at {env.current_time}\tRestorability: {restorability}')
        # accummulating the totals in the environment object


        env.number_disrupted_services += number_disrupted_services
        env.number_restored_services += number_restored_services
        env.number_relocated_services += number_relocated_services
    
        # TODO: the code below is not thread safe and therefore might have strange formatting
        with open("results/"+env.output_folder+"/services_restoration.txt", "a") as txt:
            txt.write(f"\n\nTotal disrupted: \t\t\t{len(services_disrupted)}")
            txt.write(f"\nTotal restored (relocated): {number_restored_services} ({number_relocated_services})")
            txt.write(f"\nTotal lost: \t\t\t\t{number_lost_services}")

    env.add_event(Event(env.current_time + failure.duration, link_failure_departure, failure))

def link_failure_departure(env: 'Environment', failure: 'LinkFailure') -> None:
    # in this case, only a single link failure is at the network at a given point in time
    env.logger.debug(f'Failure repaired at time: {env.current_time}\tLink: {failure.link_to_fail}')

    # tracking departures
    env.tracked_results['link_failure_departures'].append(env.current_time)

    # put the link back in a working state
    env.topology[failure.link_to_fail[0]][failure.link_to_fail[1]]['failed'] = False

    env.setup_next_link_failure()

def disaster_arrival(env: 'Environment', disaster: 'DisasterFailure') -> None:
    from core import Event

    env.tracked_results['link_disaster_arrivals'].append(env.current_time)
    env.logger.debug(f'Disaster arrived at time: {env.current_time}')

    services_disrupted: Sequence[Service] = []  # create an empty list

    #for node in disaster.nodes:
    #    env.topology.nodes[node]['failed'] = True
        # TODO: include services traversing this node into the list

    #Deve ser uma lista com todos os servicos falhos no desastre
    # get the list of disrupted services

    # extend the list with the running services
    number_failed_again: int = 0
    number_failed_first: int = 0
    number_adjusted_disrupted_services:int = 0
    for link_failure in disaster.links:
        env.logger.debug(f' - Link failed: {link_failure}')
        env.topology[link_failure[0]][link_failure[1]]['failed'] = True
        link_failed_services = []
        link_failed_services.extend(env.topology[link_failure[0]][link_failure[1]]['running_services'])
        for failed_service in link_failed_services:
            if failed_service not in services_disrupted:
                if (failed_service.arrival_time + failed_service.holding_time - env.current_time) > 0:
                    env.logger.debug(f'Releasing resources for service {failed_service}')
                    env.release_path(failed_service)
                    queue_size = len(env.events)
                    env.remove_service_departure(failed_service)
                    if queue_size -1 != len(env.events):
                        env.logger.critical('Event not removed!')
                    # set it to a failed state
                
                    failed_service.failed = True
                    failed_service.relocated = False
                    services_disrupted.append(failed_service)

                    if failed_service.failed_before:
                        number_failed_again +=1
                    else:
                        number_adjusted_disrupted_services+=1
                        number_failed_first +=1
                        failed_service.failed_before = True

  
        
        if len(env.topology[link_failure[0]][link_failure[1]]['running_services']) != 0:
            env.logger.critical('Not all services were removed')

    #temp = int(input("insira seu numero: "))
    #AQUI
    #print(temp)
    #A lista deve ser convertida em um conjunto
    number_disrupted_services = len(services_disrupted)

    this_time_disrupted_services: int=0
    for serv in services_disrupted:
        if serv.service_disaster_id == None:
            this_time_disrupted_services+=1
            env.this_disaster_services.append(serv)
    
    for idx, serv in enumerate(env.this_disaster_services):
        for service in services_disrupted:
            if serv.service_disaster_id==None:
                service.service_disaster_id = idx
                serv=service

    # call the restoration strategy
    services_disrupted = env.restoration_policy.restore(services_disrupted)

    for idx, serv in enumerate(env.this_disaster_services):
        for service in services_disrupted:
           # print("SERVICES DISRUPTED: ",services_disrupted)
            if service.service_disaster_id == serv.service_disaster_id:
                serv = service

    for serv in env.this_disaster_services:
        if serv.failed == False:
            env.adjusted_restored+=1

    # post-process the services => compute stats
    number_lost_services: int = 0
    number_restored_services: int = 0
    number_relocated_services: int = 0
    expected_capacity_loss: float = 0
    loss_cost: float = 0
    expected_loss_cost: float = 0
    number_hops_disrupted = 0
    number_hops_restaured = 0
    number_hops_relocation = 0
    #for service in services_disrupted:
    #
    for service in services_disrupted:
        expected_capacity_loss += service.expected_risk
        if service.failed == False: 
            # service could be restored
            # expected_loss_cost += service.expected_risk * service.priority_class.expected_loss_cost
            expected_loss_cost += service.priority_class.expected_loss_cost
            
            #service.downtime = service.downtime + 18000.0  codigo ONDM       #isnt it 1800?   
            number_restored_services += 1
            # puts the connection back into the network         
            if(service.route != None):
                number_hops_restaured += service.route.hops
                if service.relocated:
                    number_relocated_services+=1
                    number_hops_relocation += service.route.hops
                    service.downtime = service.downtime + 3000.0 #tempo mudado
                else: 
                    service.downtime = service.downtime + 1800.0 #tempo mantido
        
        else:    
            # service could not be restored
            # computing the service time that can be later used to compute availability
            service.service_time = env.current_time - service.arrival_time
            # computing the availability <= 1.0
            service.availability = service.service_time / service.holding_time
            loss_cost += service.priority_class.loss_cost  
            number_lost_services+=1     
        if(service.route != None):
            number_hops_disrupted += service.route.hops

        if env.epicenter_happened:
            env.num_failed_epi+=1
            if service.failed ==False: 
                env.num_restored_epi+=1
        elif env.cascade_happened_73:
            env.num_failed_73+=1
            if service.failed ==False: 
                env.num_restored_73+=1
        elif env.cascade_happened_15:
            env.num_failed_15+=1
            if service.failed ==False: 
                env.num_restored_15+=1
        elif env.cascade_happened_5:
            env.num_failed_5+=1
            if service.failed ==False: 
                env.num_restored_5+=1
        
    # register statistics such as restorability
    
    # accummulating the totals in the environment object
    if number_disrupted_services > 0:
        restorability = number_restored_services / number_disrupted_services
        env.logger.debug(f'Failure at {env.current_time}\tRestorability: {restorability}')

    env.adjusted_disrupted_services+=this_time_disrupted_services
    env.failed_again_services += number_failed_again
    env.failed_first += number_failed_first
    env.cascade_affected_services += number_disrupted_services
    env.number_disrupted_services += number_disrupted_services
    env.total_expected_capacity_loss += expected_capacity_loss
    env.total_loss_cost += loss_cost
    env.total_lost_services+= number_lost_services
    env.total_expected_loss_cost += expected_loss_cost
    env.number_restored_services += number_restored_services
    env.number_relocated_services += number_relocated_services 
    env.total_hops_disrupted_services += number_hops_disrupted
    env.total_hops_restaured_services += number_hops_restaured
    env.total_hops_relocated_services += number_hops_relocation

    
    print("AECL: ")
    print(env.total_expected_capacity_loss)  
    
    # TODO: the code below is not thread safe and therefore might have strange formatting
    with open("results/"+env.output_folder+"/services_restoration.txt", "a") as txt:
        txt.write(f"\n\nTotal disrupted: \t\t\t{len(services_disrupted)}")
        txt.write(f"\nTotal restored (relocated): {number_restored_services} ({number_relocated_services})")
        txt.write(f"\nTotal lost: \t\t\t\t{number_lost_services}")
        txt.write(f"\nAECL: \t\t\t\t{env.total_expected_capacity_loss}")
               
    env.add_event(Event(env.current_time + disaster.duration, disaster_departure, disaster))
  

def disaster_departure(env: 'Environment', disaster: 'DisasterFailure') -> None:
    
    env.cascade_happened_73 = 0
    env.cascade_happened_15 = 0
    env.cascade_happened_5 = 0
    env.epicenter_happened = 0
    # in this case, only a single link failure is at the network at a given point in time
    env.logger.debug(f'Disaster repaired at time: {env.current_time} Links: {disaster.links}')

    # tracking departures
    env.tracked_results['link_disaster_departures'].append(env.current_time)

    # put the link back in a working state
    for link in disaster.links:
        env.topology[link[0]][link[1]]['failed'] = False
        env.topology[link[0]][link[1]]['link_failure_probability'] = 0

    for node in disaster.nodes:
        env.topology.nodes[node]['failed'] = False