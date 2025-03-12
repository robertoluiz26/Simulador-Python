import abc
import typing
from typing import Optional, Sequence
import numpy as np
if typing.TYPE_CHECKING:
    from core import Service
    from core import Environment
    from graph import Path
from typing import Tuple
from networkx import Graph
import math
import networkx as nx
import routing_policies
import os
import time

def services_sorting(self, services: Sequence['Service']):
    sorted_services = []
    services_list = []

    #As we have 4 priority classes, we iterate this loop 4 times
    for classidx in range(1,5):
        partial_services_list = []

        #For each priority class, it sorts them according to remaining time
        for s in services:
            if s.priority_class.priority == classidx:
                partial_services_list.append(s)
        sorted_services = sorted(partial_services_list, key=lambda x: (x.holding_time - (self.env.current_time - x.arrival_time)), reverse=True)

        #After sorting according to time, it appends the services to an all-services-list, thus sorting it according to priority
        for s in sorted_services:
            services_list.append(s)

    services = services_list
    print("Length after", len(services))
    return services

class RestorationPolicy(abc.ABC):

    def __init__(self) -> None:
        self.env = None
        self.name = None

    @abc.abstractclassmethod
    def restore(self, services: Sequence['Service']):
        pass

    def drop_service(self, service: 'Service') -> None:
        """
        Drops a service due to not being possible to restore it.

        Args:
            service (Service): The service to be dropped.
        """
        service.service_time = self.env.current_time - service.arrival_time
        """if service.holding_time == 0:
            for i in range(2000):
                print("service holding time == 0 ")"""

        service.availability = service.service_time / service.holding_time

class DoNotRestorePolicy(RestorationPolicy):
    def __init__(self) -> None:
        super().__init__()
        self.name = 'DNR'
    
    def restore(self, services: Sequence['Service']):
        for service in services:
            self.drop_service(service)
        return services


class PathRestorationPolicy(RestorationPolicy):
    def __init__(self) -> None:
        super().__init__()
        self.name = 'PR'
    
    def restore_path(self, service: 'Service') -> bool:
        """
        Method that tries to restore a service to the same datacenter
        it is currently associated with.

        Args:
            service (Service): _description_

        Returns:
            bool: _description_
        """
        
        # tries to get a path
        path: Optional['Path'] = routing_policies.get_shortest_path(self.env.topology, service)

        # if a path was found, sets it and returns true
        if path is not None:
            service.route = path
            print ("Encontrou caminho")
            return True
        # if not, sets None and returns False
        else:
            service.route = None
            print("Nao encontrou caminho")
            return False

    def restore(self, services: Sequence['Service']):
        # TODO: implement the method
        restored_services = 0 
        relocated_services = 0
        failed_services = 0
        # docs: https://docs.python.org/3.9/howto/sorting.html#key-functions
        #services = sorted(services, key=lambda x: x.class_priority*(x.holding_time - (self.env.current_time - x.arrival_time)))
        class1_services = []
        class2_services = []
        
        services = services_sorting(self, services)

        print("Lista de prioridades")
        for s in services:
            print(s.priority_class.priority)
        print("Lista de prioridades")
        '''
        for s in services:
            if s.priority_class.priority == 1:
                class1_services.append(s)
            elif s.priority_class.priority == 2:
                class2_services.append(s)
        class1_services = services = sorted(class1_services, key=lambda x: (x.holding_time - (self.env.current_time - x.arrival_time)))
        class2_services = services = sorted(class2_services, key=lambda x: (x.holding_time - (self.env.current_time - x.arrival_time)))
        
        services = class1_services
        for c2s in class2_services:
            services.append(c2s)
        '''
        '''
        if(services != None):
            print("remaining time: ")
            for service in services:
                print(service.remaining_time)
        else:
            return services
        '''
        for service in services:
            if self.restore_path(service):
                service.failed = False
                restored_services += 1
                self.env.provision_service(service)
                service.expected_risk = routing_policies.get_path_risk(self.env.topology, service.route)
            else:  # no alternative was found
                self.drop_service(service)
        return services


class PathRestorationWithRelocationPolicy(PathRestorationPolicy):
    def __init__(self) -> None:
        super().__init__()
        self.name = 'PRwR'

    def relocate_restore_path(self, service:'Service') -> bool:
        """
        Method that tries to find an alternative DC using the same routing
        policy as the one used for the routing of new arrivals.

        Args:
            service (Service): _description_

        Returns:
            _type_: _description_
        """
        success, dc, path = self.env.routing_policy.route(service)
        if success:
            service.route = path
            print("Realocou")
            return True
        else:
            service.route = None
            print("Nao realocou")
            return False

    def restore(self, services: Sequence['Service']):
        # TODO: implement the method
        restored_services = 0 
        relocated_services = 0
        failed_services = 0

        #service.service_time = self.env.current_time - service.arrival_time
        #service.availability = service.service_time / service.holding_time

        # remaining time = holding time - (current time - arrival time)
        # docs: https://docs.python.org/3.9/howto/sorting.html#key-functions

        services = sorted(services, key=lambda x: (x.holding_time - (self.env.current_time - x.arrival_time)), reverse=True)
        '''
        class1_services = []
        class2_services = []
        
        #Sorts the services according to priority classes
        services = services_sorting(self, services)

        print("Lista de prioridades")
        for s in services:
            print(s.priority_class.priority)
        print("Lista de prioridades")
        '''
        """
        for s in services:
            if s.priority_class.priority == 1:
                class1_services.append(s)
            elif s.priority_class.priority == 2:
                class2_services.append(s)
        class1_services = services = sorted(class1_services, key=lambda x: (x.holding_time - (self.env.current_time - x.arrival_time)))
        class2_services = services = sorted(class2_services, key=lambda x: (x.holding_time - (self.env.current_time - x.arrival_time)))
        
        services = class1_services
        for c2s in class2_services:
            services.append(c2s)
        """
        '''
        if(services != None):
            print("remaining time: ")
            for service in services:
                print(service.remaining_time)
        else:
            return services
        '''
        tempo = 0
        falha_total = 0
        for service in services:
            print('trying', service)
            if(service.holding_time - (self.env.current_time - service.arrival_time))>1800.0:
                tempo_inicial = time.time()
                if self.restore_path(service):
                    service.failed = False
                    restored_services += 1
                    self.env.provision_service(service)
                    service.expected_risk = routing_policies.get_path_risk(self.env.topology, service.route)
                elif self.relocate_restore_path(service):
                    service.failed = False
                    service.relocated = True
                    restored_services += 1
                    relocated_services += 1
                    self.env.provision_service(service)
                    service.expected_risk = routing_policies.get_path_risk(self.env.topology, service.route)
                else:  # no alternative was found
                    self.drop_service(service)
                tempo_final = time.time()
                if not service.failed:
                    tempo += (tempo_final - tempo_inicial)
                    failures_list = []
                    print(type(service.route))

                    for i in range(service.route.hops):
                        link = self.env.topology[service.route.node_list[i]][service.route.node_list[i + 1]]
                        failures_list.append(1 - link['current_failure_probability'])
                    failure = 1 
                    for f in failures_list:
                        failure *= f
                    falha = 1 - failure
                    falha_total += falha
                    
            else:  # no alternative was found
                self.drop_service(service)
                failed_services+=1
            
        print("perdidos: ")
        print(failed_services)
        self.env.restorability_time += tempo
        """diretorio_log = "log_tempo"
        
        if not os.path.exists(diretorio_log):
            os.makedirs(diretorio_log)
        arquivo = os.path.join(diretorio_log,"log_tempo_pwrp.txt")
        
        # Abre o arquivo (cria se não existir) e escreve a mensagem
        if os.path.exists(arquivo):
            # Abre o arquivo em modo de acréscimo ('append')
            with open(arquivo, 'a') as f:
                f.write('time to relocate: ' + str(tempo)+ "\n")
                
        else:
            # Cria um novo arquivo e escreve a mensagem
            with open(arquivo, 'w') as f:
                f.write('time to relocate: ' + str(tempo)+ "\n")"""
                
        self.env.failure_probability += falha_total
        return services


class PathRestorationPropabilitiesAware(RestorationPolicy):
    def __init__(self) -> None:
        super().__init__()
        self.name = 'PRPA(α=1)'
    
    def restore_path(self, service: 'Service') -> bool:
        """
        Method that tries to restore a service to the same datacenter
        it is currently associated with.

        Args:
            service (Service): _description_

        Returns:
            bool: _description_
        """
        
        #print("chama safest")
        # tries to get a path
        #print("entrada>>get_safest_path")
        path: Optional['Path'] = routing_policies.get_safest_path(self.env.topology, service) 
        #print("get_safest_path>>saida")
        #path: Optional['Path'] = routing_policies.get_shortest_path(self.env.topology, service)#(juliana alteracao)
        #print("returned by safest: ")
        # if a path was found, sets it and returns true
        if path is not None:
            service.route = path
            print ("Encontrou caminho")
            return True
        # if not, sets None and returns False
        else:
            service.route = None
            print("Nao encontrou caminho")
            return False
    def relocate_restore_path(self, service:'Service') -> bool:
        """
        Method that tries to find an alternative DC using the same routing
        policy as the one used for the routing of new arrivals.

        Args:
            service (Service): _description_

        Returns:
            _type_: _description_
        """
        success, dc, path = routing_policies.get_safest_dc(self.env.topology, service)#duvida: onde?
        if success:
            service.route = path
            print("Realocou")
            return True
        else:
            service.route = None
            print("Nao realocou")
            return False
    def restore(self, services: Sequence['Service']):
        # TODO: implement the method
        restored_services = 0 
        relocated_services = 0
        failed_services = 0
        
        # docs: https://docs.python.org/3.9/howto/sorting.html#key-functions
        #services = sorted(services, key=lambda x: x.class_priority*(x.holding_time - (self.env.current_time - x.arrival_time)))
        services = sorted(services, key=lambda x: (x.holding_time - (self.env.current_time - x.arrival_time)), reverse=True)
        
        #services = services_sorting(self, services)

        """
        for s in services:
            if s.priority_class.priority == 1:
                class1_services.append(s)
            elif s.priority_class.priority == 2:
                class2_services.append(s)
            elif s.priority_class.priority == 3:
                class3_services.append(s)
            elif s.priority_class.priority == 4:
                class4_services.append(s)
        class1_services = services = sorted(class1_services, key=lambda x: (x.holding_time - (self.env.current_time - x.arrival_time)))
        class2_services = services = sorted(class2_services, key=lambda x: (x.holding_time - (self.env.current_time - x.arrival_time)))
        
        services = class1_services
        for c2s in class2_services:
            services.append(c2s)
        """

        '''
        if(services != None):
            print("remaining time: ")
            for service in services:
                print(service.remaining_time)
        else:
            return services
        '''
        tempo = 0
        falha_total = 0
        for service in services:
            if(service.holding_time - (self.env.current_time - service.arrival_time))>1800.0:
                tempo_inicial = time.time()               
                if self.restore_path(service):
                    service.failed = False
                    restored_services += 1
                    self.env.provision_service(service)
                    service.expected_risk = routing_policies.get_path_risk(self.env.topology, service.route)
                elif self.relocate_restore_path(service):
                    service.failed = False
                    service.relocated = True
                    restored_services += 1
                    relocated_services += 1
                    self.env.provision_service(service)
                    service.expected_risk = routing_policies.get_path_risk(self.env.topology, service.route)
                else:  # no alternative was found
                    self.drop_service(service)
                tempo_final = time.time()
                if not service.failed:
                    tempo += (tempo_final - tempo_inicial)
                    failures_list = []
                    for i in range(service.route.hops):
                        link = self.env.topology[service.route.node_list[i]][service.route.node_list[i + 1]]
                        failures_list.append(1 - link['current_failure_probability'])
                    failure = 1 
                    for f in failures_list:
                        failure *= f
                    falha = 1 - failure
                    falha_total += falha
            else:  # no alternative was found
                self.drop_service(service)
        self.env.restorability_time += tempo    
        self.env.failure_probability += falha_total
        return services

class PathRestorationBalancedPropabilitiesAware(RestorationPolicy):
    def __init__(self) -> None:
        super().__init__()
        self.name = 'PRPA(α=0.5)'
    
    def restore_path(self, service: 'Service') -> bool:
        """
        Method that tries to restore a service to the same datacenter
        it is currently associated with.

        Args:
            service (Service): _description_

        Returns:
            bool: _description_
        """
        
        #print("chama safest")
        # tries to get a path
        #print("entrada>>get_safest_path")
        path: Optional['Path'] = routing_policies.get_balanced_sasfest_path(self.env.topology, service) 
        #print("get_safest_path>>saida")
        #path: Optional['Path'] = routing_policies.get_shortest_path(self.env.topology, service)#(juliana alteracao)
        #print("returned by safest: ")
        # if a path was found, sets it and returns true
        if path is not None:
            service.route = path
            print ("Encontrou caminho")
            return True
        # if not, sets None and returns False
        else:
            service.route = None
            print("Nao encontrou caminho")
            return False
    def relocate_restore_path(self, service:'Service') -> bool:
        """
        Method that tries to find an alternative DC using the same routing
        policy as the one used for the routing of new arrivals.

        Args:
            service (Service): _description_

        Returns:
            _type_: _description_
        """
        success, dc, path = routing_policies.get_balanced_safest_dc(self.env.topology, service)#duvida: onde?
        if success:
            service.route = path
            print("Realocou")
            return True
        else:
            service.route = None
            print("Nao realocou")
            return False
    def restore(self, services: Sequence['Service']):
        # TODO: implement the method
        restored_services = 0 
        relocated_services = 0
        failed_services = 0
        tempo = 0
        falha_total = 0 
        # docs: https://docs.python.org/3.9/howto/sorting.html#key-functions
        #services = sorted(services, key=lambda x: x.class_priority*(x.holding_time - (self.env.current_time - x.arrival_time)))
        services = sorted(services, key=lambda x: (x.holding_time - (self.env.current_time - x.arrival_time)), reverse=True)
                #print(f"A condição foi registrada no arquivo '{arquivo}'")
        for service in services:
            if(service.holding_time - (self.env.current_time - service.arrival_time))>1800.0:
                tempo_inicial = time.time()
                if self.restore_path(service):
                    service.failed = False
                    restored_services += 1
                    self.env.provision_service(service)
                    service.expected_risk = routing_policies.get_path_risk(self.env.topology, service.route)
                elif self.relocate_restore_path(service):
                    service.failed = False
                    service.relocated = True
                    restored_services += 1
                    relocated_services += 1
                    self.env.provision_service(service)
                    service.expected_risk = routing_policies.get_path_risk(self.env.topology, service.route)
                else:  # no alternative was found
                    self.drop_service(service)
                tempo_final = time.time()
                if not service.failed:
                    tempo += (tempo_final - tempo_inicial)
                    failures_list = []
                    for i in range(service.route.hops):
                        link = self.env.topology[service.route.node_list[i]][service.route.node_list[i + 1]]
                        failures_list.append(1 - link['current_failure_probability'])
                    failure = 1 
                    for f in failures_list:
                        failure *= f
                    falha = 1 - failure
                    falha_total += falha
            else:  # no alternative was found
                self.drop_service(service)
        self.env.restorability_time += tempo           
        self.env.failure_probability += falha_total

        """diretorio_log = "log_tempo"
        if not os.path.exists(diretorio_log):
            os.makedirs(diretorio_log)
        arquivo = os.path.join(diretorio_log,"log_tempo_prpa_05.txt")
        
        # Abre o arquivo (cria se não existir) e escreve a mensagem
        if os.path.exists(arquivo):
            # Abre o arquivo em modo de acréscimo ('append')
            with open(arquivo, 'a') as f:
                f.write('time to relocate: ' + str(tempo)+ "\n")
                
        else:
            # Cria um novo arquivo e escreve a mensagem
            with open(arquivo, 'w') as f:
                f.write('time to relocate: ' + str(tempo)+ "\n")"""
        return services
    
class PathRestorationBalancedPropabilitiesAware04(RestorationPolicy):
    def __init__(self) -> None:
        super().__init__()
        self.name = 'PRPA(α=0.4)'
    
    def restore_path(self, service: 'Service') -> bool:
        """
        Method that tries to restore a service to the same datacenter
        it is currently associated with.

        Args:
            service (Service): _description_

        Returns:
            bool: _description_
        """
        
        #print("chama safest")
        # tries to get a path
        #print("entrada>>get_safest_path")
        path: Optional['Path'] = routing_policies.get_path_alfa_04(self.env.topology, service) 
        #print("get_safest_path>>saida")
        #path: Optional['Path'] = routing_policies.get_shortest_path(self.env.topology, service)#(juliana alteracao)
        #print("returned by safest: ")
        # if a path was found, sets it and returns true
        if path is not None:
            service.route = path
            print ("Encontrou caminho")
            return True
        # if not, sets None and returns False
        else:
            service.route = None
            print("Nao encontrou caminho")
            return False
    def relocate_restore_path(self, service:'Service') -> bool:
        """
        Method that tries to find an alternative DC using the same routing
        policy as the one used for the routing of new arrivals.

        Args:
            service (Service): _description_

        Returns:
            _type_: _description_
        """
        success, dc, path = routing_policies.get_dc_alfa_04(self.env.topology, service)#duvida: onde?
        if success:
            service.route = path
            print("Realocou")
            return True
        else:
            service.route = None
            print("Nao realocou")
            return False
    def restore(self, services: Sequence['Service']):
        # TODO: implement the method
        restored_services = 0 
        relocated_services = 0
        failed_services = 0
        tempo = 0
        falha_total = 0
        # docs: https://docs.python.org/3.9/howto/sorting.html#key-functions
        #services = sorted(services, key=lambda x: x.class_priority*(x.holding_time - (self.env.current_time - x.arrival_time)))
        services = sorted(services, key=lambda x: (x.holding_time - (self.env.current_time - x.arrival_time)), reverse=True)
        for service in services:
            if(service.holding_time - (self.env.current_time - service.arrival_time))>1800.0:
                tempo_inicial = time.time()
                if self.restore_path(service):
                    service.failed = False
                    restored_services += 1
                    self.env.provision_service(service)
                    service.expected_risk = routing_policies.get_path_risk(self.env.topology, service.route)
                elif self.relocate_restore_path(service):
                    service.failed = False
                    service.relocated = True
                    restored_services += 1
                    relocated_services += 1
                    self.env.provision_service(service)
                    service.expected_risk = routing_policies.get_path_risk(self.env.topology, service.route)
                else:  # no alternative was found
                    self.drop_service(service)
                tempo_final = time.time()
                if not service.failed:
                    tempo += (tempo_final - tempo_inicial)
                    failures_list = []
                    for i in range(service.route.hops):
                        link = self.env.topology[service.route.node_list[i]][service.route.node_list[i + 1]]
                        failures_list.append(1 - link['current_failure_probability'])
                    failure = 1 
                    for f in failures_list:
                        failure *= f
                    falha = 1 - failure
                    falha_total += falha
            else:  # no alternative was found
                self.drop_service(service)
        self.env.restorability_time += tempo        
        self.env.failure_probability += falha_total
        return services
    
class PathRestorationBalancedPropabilitiesAware03(RestorationPolicy):
    def __init__(self) -> None:
        super().__init__()
        self.name = 'PRPA(α=0.3)'
    
    def restore_path(self, service: 'Service') -> bool:
        """
        Method that tries to restore a service to the same datacenter
        it is currently associated with.

        Args:
            service (Service): _description_

        Returns:
            bool: _description_
        """
        
        #print("chama safest")
        # tries to get a path
        #print("entrada>>get_safest_path")
        path: Optional['Path'] = routing_policies.get_path_alfa_03(self.env.topology, service) 
        #print("get_safest_path>>saida")
        #path: Optional['Path'] = routing_policies.get_shortest_path(self.env.topology, service)#(juliana alteracao)
        #print("returned by safest: ")
        # if a path was found, sets it and returns true
        if path is not None:
            service.route = path
            print ("Encontrou caminho")
            return True
        # if not, sets None and returns False
        else:
            service.route = None
            print("Nao encontrou caminho")
            return False
    def relocate_restore_path(self, service:'Service') -> bool:
        """
        Method that tries to find an alternative DC using the same routing
        policy as the one used for the routing of new arrivals.

        Args:
            service (Service): _description_

        Returns:
            _type_: _description_
        """
        success, dc, path = routing_policies.get_dc_alfa_03(self.env.topology, service)#duvida: onde?
        if success:
            service.route = path
            print("Realocou")
            return True
        else:
            service.route = None
            print("Nao realocou")
            return False
    def restore(self, services: Sequence['Service']):
        # TODO: implement the method
        restored_services = 0 
        relocated_services = 0
        failed_services = 0
        tempo = 0
        falha_total = 0
        # docs: https://docs.python.org/3.9/howto/sorting.html#key-functions
        #services = sorted(services, key=lambda x: x.class_priority*(x.holding_time - (self.env.current_time - x.arrival_time)))
        services = sorted(services, key=lambda x: (x.holding_time - (self.env.current_time - x.arrival_time)), reverse=True)
        for service in services:
            if(service.holding_time - (self.env.current_time - service.arrival_time))>1800.0:
                tempo_inicial = time.time()
                if self.restore_path(service):
                    service.failed = False
                    restored_services += 1
                    self.env.provision_service(service)
                    service.expected_risk = routing_policies.get_path_risk(self.env.topology, service.route)
                elif self.relocate_restore_path(service):
                    service.failed = False
                    service.relocated = True
                    restored_services += 1
                    relocated_services += 1
                    self.env.provision_service(service)
                    service.expected_risk = routing_policies.get_path_risk(self.env.topology, service.route)
                else:  # no alternative was found
                    self.drop_service(service)
                tempo_final = time.time()
                if not service.failed:
                    tempo += (tempo_final - tempo_inicial)
                    failures_list = []
                    for i in range(service.route.hops):
                        link = self.env.topology[service.route.node_list[i]][service.route.node_list[i + 1]]
                        failures_list.append(1 - link['current_failure_probability'])
                    failure = 1 
                    for f in failures_list:
                        failure *= f
                    falha = 1 - failure
                    falha_total += falha
            else:  # no alternative was foundarrival_time
                self.drop_service(service)
                
        self.env.restorability_time += tempo
        self.env.failure_probability += falha_total
        return services
    
class PathRestorationBalancedPropabilitiesAware01(RestorationPolicy):
    def __init__(self) -> None:
        super().__init__()
        self.name = 'PRPA(α=0.1)'
    
    def restore_path(self, service: 'Service') -> bool:
        """
        Method that tries to restore a service to the same datacenter
        it is currently associated with.

        Args:
            service (Service): _description_

        Returns:
            bool: _description_
        """
        
        #print("chama safest")
        # tries to get a path
        #print("entrada>>get_safest_path")
        path: Optional['Path'] = routing_policies.get_path_alfa_01(self.env.topology, service) 
        #print("get_safest_path>>saida")
        #path: Optional['Path'] = routing_policies.get_shortest_path(self.env.topology, service)#(juliana alteracao)
        #print("returned by safest: ")
        # if a path was found, sets it and returns true
        if path is not None:
            service.route = path
            print ("Encontrou caminho")
            return True
        # if not, sets None and returns False
        else:
            service.route = None
            print("Nao encontrou caminho")
            return False
    def relocate_restore_path(self, service:'Service') -> bool:
        """
        Method that tries to find an alternative DC using the same routing
        policy as the one used for the routing of new arrivals.

        Args:
            service (Service): _description_

        Returns:
            _type_: _description_
        """
        success, dc, path = routing_policies.get_dc_alfa_01(self.env.topology, service)#duvida: onde?
        if success:
            service.route = path
            print("Realocou")
            return True
        else:
            service.route = None
            print("Nao realocou")
            return False
    def restore(self, services: Sequence['Service']):
        # TODO: implement the method
        restored_services = 0 
        relocated_services = 0
        failed_services = 0
        tempo = 0
        falha_total = 0
        # docs: https://docs.python.org/3.9/howto/sorting.html#key-functions
        #services = sorted(services, key=lambda x: x.class_priority*(x.holding_time - (self.env.current_time - x.arrival_time)))
        services = sorted(services, key=lambda x: (x.holding_time - (self.env.current_time - x.arrival_time)), reverse=True)

        for service in services:
            #if service.remaining_time > 1800.0: 
            if(service.holding_time - (self.env.current_time - service.arrival_time))>1800.0:
                tempo_inicial = time.time()
                if self.restore_path(service):
                    service.failed = False
                    restored_services += 1
                    self.env.provision_service(service)
                    service.expected_risk = routing_policies.get_path_risk(self.env.topology, service.route)
                elif self.relocate_restore_path(service):
                    service.failed = False
                    service.relocated = True
                    restored_services += 1
                    relocated_services += 1
                    self.env.provision_service(service)
                    service.expected_risk = routing_policies.get_path_risk(self.env.topology, service.route)
                else:  # no alternative was found
                    self.drop_service(service)
                tempo_final = time.time()
                if not service.failed:
                    tempo += (tempo_final - tempo_inicial)
                    failures_list = []
                    for i in range(service.route.hops):
                        link = self.env.topology[service.route.node_list[i]][service.route.node_list[i + 1]]
                        failures_list.append(1 - link['current_failure_probability'])
                    failure = 1 
                    for f in failures_list:
                        failure *= f
                    falha = 1 - failure
                    falha_total += falha
            else:  # no alternative was found
                self.drop_service(service)
        self.env.restorability_time += tempo
        self.env.failure_probability += falha_total
        return services

class ILP_probability_awareness(RestorationPolicy):
    def __init__(self, cont) -> None:
        super().__init__()
        self.name = 'ILP'
        self.cont = cont
    
    def generate_ILP(self, services: Sequence['Service'], alpha:int):
        #print("ENTROU GENERATE ILP 1")
        #print("self.cont = ", self.cont)
        if not os.path.exists("arquivos_otimizacao"):
            os.makedirs("arquivos_otimizacao")
        nome = './arquivos_otimizacao/gurobi_otimizacao' + '_'+ str(self.cont) +'_'+ str(alpha)+ "_" +str(int(self.env.current_time))+'.lp'
        #print("nome: ", nome)
        #print("nome: ", nome)
        sumNormalizedTime = 0
        normalizedRelocationTime = 0 
        normalizedRestorationTime = 0
        greaterRemainingTime = 0  
        usa_tempo = True
        for service in services:
            #print("service.remaining_time = ", service.remaining_time)
            if greaterRemainingTime < (service.holding_time - (self.env.current_time - service.arrival_time)):
                greaterRemainingTime = service.holding_time - self.env.current_time + service.arrival_time
        print("achou greaterRemainingTime: ", greaterRemainingTime)

        
        with open(nome, 'w') as lp:
            lp.write("Minimize wls + 1000 relocations  + 10000 unrestored_time  + 10000 total_cost \n") # diminui relocations de 1000 para 100
            #print("ENTROU GENERATE ILP 4")
           
        #   sujeito a:
            lp.write("Subject to\n")
            #print("flow conservation")
            #flow conservation
            for service in services:
                for node in self.env.topology.nodes():
                    first = True
                    if service.source == node:
                        for nb in list(self.env.topology.neighbors(node)):
                            link = self.env.topology[node][nb]
                            if link['current_failure_probability'] != 1:
                                if not first:
                                    lp.write(" + ")
                                else:
                                    first = False
                                lp.write("x_" + str(service.service_id) + "_" + str(link['id']))
                        lp.write(" - restored_" + str(service.service_id) + " = 0 \n")
                    elif self.env.topology.nodes[node]['dc']:
                        for nb in list(self.env.topology.neighbors(node)):
                            link = self.env.topology[node][nb]
                            if link['current_failure_probability'] != 1:
                                if not first:
                                    lp.write(" + ")
                                else:
                                    first = False
                                lp.write("x_" + str(service.service_id) + "_" + str(link['id']))
                        lp.write(" - restored_dc_" + str(service.service_id) + "_" + str(node)+ " = 0 \n")
                    elif node != service.source:
                        for nb in list(self.env.topology.neighbors(node)):
                            link = self.env.topology[node][nb]
                            if link['current_failure_probability'] != 1:
                                if not first:
                                    lp.write(" + ")
                                else:
                                    first = False
                                lp.write("x_" + str(service.service_id) + "_" + str(link['id']))
                        lp.write(" - 2 restored_node_" + str(service.service_id) + "_" + str(node) + " = 0 \n")
            #eq. 6 paper:
            #print("eq. 6 paper: ")
            for lnk in self.env.topology.edges():
                link = self.env.topology[lnk[0]][lnk[1]]
                if link['current_failure_probability'] != 1:
                    first = True
                    for service in services:
                        if not first:
                            lp.write(" + ")
                        else:
                            first = False
                        lp.write("x_" + str(service.service_id)+ "_" + str(link['id']))
                    lp.write(" - load_" + str(link['id']) + " = 0\n")
            #print("load <= available units")
            for lnk in self.env.topology.edges():
                link = self.env.topology[lnk[0]][lnk[1]]
                if link['current_failure_probability'] != 1:
                    lp.write("load_" + str(self.env.topology[lnk[0]][lnk[1]]['id']) + " <= " + str(self.env.topology[lnk[0]][lnk[1]]['available_units'])+"\n")
            #print("get required computing units")
            #get required computing units
            for node in self.env.topology.nodes():
                if self.env.topology.nodes[node]['dc']:
                    first = True
                    for service in services:
                        if not first:
                            lp.write(" + ")
                        else:
                            first = False
                        lp.write( str(service.computing_units) + " restore_dc_" + str(service.service_id) + "_" + str(node))
                    lp.write(" <= " + str(self.env.topology.nodes[node]['available_units']) + "\n")
            first = True
            total = 0
            #print("calcula as wavelengths utilizadas")
            #calcula as wavelengths utilizadas
            for lnk in self.env.topology.edges():
                link = self.env.topology[lnk[0]][lnk[1]]
                if link['current_failure_probability'] != 1:
                    total += link['available_units']
                    if not first:
                        lp.write(" + ")
                    else:
                        first = False
                    lp.write("load_" + str(link['id']))
            lp.write(" - wls = 0 \n")
            first = True
            #print("restored")
            for service in services:
                if not first:
                    lp.write(" + ")
                else:
                    first = False
                lp.write("restored_" + str(service.service_id))
            lp.write(" - restored = 0 \n")
            #print("serviços restaurados + não restaurados = total de serviços")
            #serviços restaurados + não restaurados = total de serviços
            lp.write("unrestored + restored = " + str(len(services))+ "\n")
            
            #print("serviço só pode ser restaurado em um DC")
            #serviço só pode ser restaurado em um DC
            for service in services:
                first = True
                for node in self.env.topology.nodes():
                    if self.env.topology.nodes[node]['dc']:
                        if not first:
                            lp.write(" + ")
                        else:
                            first = False
                        lp.write("restored_dc_" + str(service.service_id) + "_" + str(node))
                lp.write(" <= 1 \n")
            #se o serviço precisar ser realocado, só será realocado para um DC
            #print("#se o serviço precisar ser realocado, só será realocado para um DC")
            for service in services:
                first = True
                for node in self.env.topology.nodes():
                    #print("Entrou se realocado")
                    #print("service destination: ", service.destination)
                    #print("node: ", node)
                    if self.env.topology.nodes[node]['dc'] and node != service.destination:
                        if not first:
                            lp.write(" + ")
                        else:
                            lp.write("restored_dc_" + str(service.service_id) + "_" + str(node))
                        lp.write(" - relocation_" + str (service.service_id) + " = 0 \n")
            #calcula o numero de realocações realizadas
            #print("#calcula o numero de realocações realizadas")
            first = True
            for service in services:
                if not first:
                    lp.write(" + ")
                else:
                    first = False
                lp.write("relocation_" + str(service.service_id))
            lp.write(" - relocations = 0 \n")
            #print("total_cost")
            first = True
            for service in services:
                if not first:
                    lp.write(" + ")
                else:
                    first = False
                lp.write("path_" + str(service.service_id))
            lp.write(" - total_cost = 0\n")
            #print("probability")
            for service in services:
                first = True
                for lnk in self.env.topology.edges():
                    link = self.env.topology[lnk[0]][lnk[1]]
                    if link['current_failure_probability'] != 1:
                        if not first:
                            lp.write(" + ")
                        else:
                            first = False
                        #print("entrou failure probability")
                        
                        if link['current_failure_probability'] == 0:
                            ln_prob = 1
                        else:
                            ln_prob = round(math.log(1 - link['current_failure_probability']), 2) * (-100)
                        lp.write(" " + str(ln_prob) + " x_" + str(service.service_id) + "_" + str(link['id']))
                    
                lp.write(" - path_" + str(service.service_id) + " = 0\n")
            first = True
            factor = 10000
            lightSpeed = 300000
            #print("unrestored time")
            for service in services: 
                #print("entra services")
                for node in self.env.topology.nodes():
                    #print("entra nodes")
                    if self.env.topology.nodes[node]['dc']: #and node != service.destination: 
                        #print("if self.env.topology.nodes[node]['dc']:")
                        #print("(service.holding_time - (self.env.current_time - service.arrival_time)): ", (service.holding_time - (self.env.current_time - service.arrival_time)))
                        normalizedRemainingTime = int(math.ceil(factor * (service.arrival_time + service.holding_time - self.env.current_time)/(greaterRemainingTime)))
                        sumNormalizedTime += normalizedRemainingTime
                        if service.destination == node:
                            #print("if service.destination == node:")
                            if not first:
                                lp.write(" + ")
                            else:
                                first = False
                            lp.write(str(normalizedRemainingTime) + " restored_dc_" + str(service.service_id) + "_" + str(node))
                        else:
                            #print("else")
                            #relocation time: caminho mais rapido entre DCs distancia_total/velocidade_da_luz * factor
                            shortest_distance = nx.shortest_path_length(self.env.topology, source=service.source, target=node, weight='length')
                            relocationTime = float (shortest_distance/lightSpeed)
                            normalizedRelocationTime = int((relocationTime/greaterRemainingTime)*factor)
                            if normalizedRelocationTime < normalizedRemainingTime:
                                if not first:
                                    lp.write(" + ")
                                else:
                                    first = False
                                lp.write(str(normalizedRemainingTime - normalizedRelocationTime) + " restored_dc_" + str(service.service_id) + "_" + str(node))
            lp.write(" - restored_time = 0 \n")
            lp.write("unrestored_time + restored_time = " + str(sumNormalizedTime) + "\n")
            #print("binary")
            lp.write("Binary \n")
            for service in services:
                for node in self.env.topology.nodes():
                    if (not self.env.topology.nodes[node]['dc']) and node != service.destination and node != service.source:
                        lp.write("restored_node_" + str(service.service_id) + "_" + str(node) + "\n")
                    elif self.env.topology.nodes[node]['dc']:
                        lp.write("restored_dc_" + str(service.service_id) + "_" + str(node) + "\n")
                for lnk in self.env.topology.edges():
                    link = self.env.topology[lnk[0]][lnk[1]]

                    if link['current_failure_probability'] != 1:
                        lp.write("x_"+ str(service.service_id) + "_" + str(link['id']) + "\n")
                lp.write("restored_" + str(service.service_id) + "\n")
                lp.write("relocation_" + str(service.service_id) + "\n")
            #print("general")
            lp.write("General \n")
            for lnk in self.env.topology.edges():
                link = self.env.topology[lnk[0]][lnk[1]]
                if link['current_failure_probability'] != 1:
                    lp.write("load_" + str(link ['id']) + "\n")
                
            for service in services:
                lp.write("path_" + str(service.service_id) + "\n")

            lp.write("restored \n")
            lp.write("restored_time \n")
            lp.write("unrestored_time \n")
            lp.write("unrestored \n")
            lp.write("relocations \n")
            lp.write("total_cost \n")
            lp.write("wls \n")
            lp.write("END \n")
            print("SAIU GENERATE ILP")
        
    def restore(self, services: Sequence['Service']):
        print("ENTROU RESTORE ILP!!!")
        contador = 0
        acabou = False
        resultado: Sequence['Service'] = []
        total_hops = 0
        probabilidade_total = 0
        tempo = 0
        falha_total = 0
        services_queda: Sequence['Service'] = []
        #print("len dos serviços antes da organização: ", len(services))
        services = sorted(services, key=lambda x: x.arrival_time - (self.env.current_time - x.holding_time) , reverse=True)
        #print("len: ", len(services))
        #print("services: ", services)
        for service in services[:]:
            if (service.holding_time + service.arrival_time - self.env.current_time) < 1800.0:
                services.remove(service)
                services_queda.append(service)

        for service in services_queda:
            service.route = None
            self.drop_service(service)


        while services:
            #print("EXISTE SERVICES  ")
            svs = services[:80]
            #print("len svs: ", len(svs))
            #print("svs: ", svs)
            if not svs:
                break
            #print("dividiu svs em um batch de 80 services")
            services = services[80:]
            #print("pega os proximos 80 services")
            self.generate_ILP(svs, contador)
            #print("generate PLI")
        #print("SAIU RESTORE")
            import gurobipy as gp
            from gurobipy import GRB
            from graph import Path
            #print("Entrou na otimização")
            # Crie um objeto de modelo

            arq = './arquivos_otimizacao/gurobi_otimizacao'+'_'+ str(self.cont) +'_' + str(contador) + "_" + str(int(self.env.current_time)) +'.lp'
            contador += 1
            # Crie um objeto de modelo
            model = gp.read(arq)
            model.setParam(GRB.Param.TimeLimit, 120)
            #model.setParam(GRB.Param.MIPGap, 0.0)  # Definir a tolerância do gap para 0 para resultados mais exatos
            #model.setParam(GRB.Param.IntegralityFocus, 1)  # Focar mais na integridade das variáveis

            # Otimize o modelo
            model.optimize()
            print("arquivo otimizado foi: " + arq)
            print("otimizou com sucesso! ")
            
            # Verifique o status da otimização print("não serviços nao podem ser restaurados")
            if model.Status == GRB.OPTIMAL or (model.Status == GRB.TIME_LIMIT and model.solCount > 0):   #se a solução for ótima ou achou uma solução dentro do tempo
                #total hops será o número de wls usadas:
                tempo += model.Runtime
                print("É ÓTIMO OU TEM UMA SOLUÇÃO")
                total_hops += model.getVarByName('wls').x
                #para cada serviço, verifique qual dc foi utilizado:              
                for service in svs:
                    total_length = 0
                    restaurado = False
                    path = []
                    for node in self.env.topology.nodes():
                        if self.env.topology.nodes[node]['dc']:
                            name = 'restored_dc_' + str(service.service_id) + '_' + str(node)
                            if model.getVarByName(name).x == 1: #foi achado o dc para o qual o serviço foi restaurado
                                #print("É POSSIVEL SER RESTAURADO")
                                if node != service.destination:
                                    #print("SERVIÇO REALOCADO")
                                    service.relocated = True
                                service.failed = False
                                failures_list = []
                                #finished = False
                                source = service.source
                                path.append(source)
                                found = False
                                while not found:
                                    #print("WHILE NOT FOUND")
                                    #print("arq: ", arq)
                                    #print("serviço: ", service.service_id)
                                    for nb in list(self.env.topology.neighbors(source)):
                                        link = self.env.topology[source][nb]
                                        if link['current_failure_probability'] != 1:
                                            st = 'x_' + str(service.service_id) + '_' + str(link['id'])
                                            valor = round(model.getVarByName(st).x)
                                            if valor == 1:
                                                if nb not in path:
                                                    path.append(nb)
                                                    source = nb
                                                    failures_list.append(1 - link['current_failure_probability'])
                                                    break
                                    if source == node:
                                        found = True           

                                #print("saiu do for")
                                failure = 1 
                                for f in failures_list:
                                    failure *= f
                                falha = 1 - failure
                                service.expected_risk = falha
                                falha_total += falha
                                restaurado = True
                                #print("ACHOU A FALHA ESPERADA")
                                break
                        
                    if not restaurado:
                        #print("NÃO É POSSÍVEL SER RESTAURADO")
                        service.route = None
                        self.drop_service(service)

                    else:
                        #print("ESTA CALCULANDO A LENGTH")
                        for i in range(len(path) - 1):
                            link = self.env.topology[path[i]][path[i + 1]]
                            total_length += link["length"]
                        #print("ACHOU A LENGTH")
                        new_path = Path(path,total_length)
                        service.route = new_path 
                        self.env.provision_service(service)        
                        #print("ACHOU O PATH")
                #print(f"Valor da função objetivo: {model.objVal}")  
            elif model.Status == GRB.TIME_LIMIT and model.solCount <= 0:
                #print("NÃO FOI ENCONTRADA UM PATH POIS ESTOUROU O TEMPO")
                for service in services:
                    service.route = None
                    self.drop_service(service)
            else:
                #print("Não foi encontrada uma solução ótima.")
                for service in svs:
                    
                    service.route = None
                    self.drop_service(service)
            if model.Status == GRB.TIME_LIMIT and model.solCount > 0:
                diretorio_log = "log_pli"
                objective_bound = model.ObjBound
                mipgap = model.MIPGap
                if not os.path.exists(diretorio_log):
                    os.makedirs(diretorio_log)
                arquivo = os.path.join(diretorio_log, "log_pli_gurobi.txt")
            
                # Abre o arquivo (cria se não existir) e escreve a mensagem
                if os.path.exists(arquivo):
                    # Abre o arquivo em modo de acréscimo ('append')
                    with open(arquivo, 'a') as f:
                        f.write('model.Status == GRB.TIME_LIMIT and model.solCount > 0in the arquive: ' + arq + "\n")
                        f.write("the bound is " + str(objective_bound) + "\n")
                        f.write("The MIPGap is "+ str(mipgap)+ "\n")
                else:
                    # Cria um novo arquivo e escreve a mensagem
                    with open(arquivo, 'w') as f:
                        f.write('model.Status == GRB.TIME_LIMIT and model.solCount > 0.\n')
                        f.write("the bound is " + str(objective_bound) + "\n")
                        f.write("The MIPGap is "+ str(mipgap)+ "\n")
            elif model.Status == GRB.TIME_LIMIT and model.solCount <= 0:
                diretorio_log = "log_pli"
                objective_bound = model.ObjBound
                if not os.path.exists(diretorio_log):
                    os.makedirs(diretorio_log)
                
                arquivo = os.path.join(diretorio_log,"log_pli_gurobi_wrong.txt")
                # Abre o arquivo (cria se não existir) e escreve a mensagem
                if os.path.exists(arquivo):
                    # Abre o arquivo em modo de acréscimo ('append')
                    with open(arquivo, 'a') as f:
                        f.write('model.Status == GRB.TIME_LIMIT and model.solCount <= 0\n')
                else:
                    # Cria um novo arquivo e escreve a mensagem
                    with open(arquivo, 'w') as f:
                        f.write('model.Status == GRB.TIME_LIMIT and model.solCount <= 0\n')
            resultado.extend(svs)
            model.close()
            #print("ELE SAI DA EXECUÇÃO")
        resultado.extend(services_queda)
        self.env.restorability_time += tempo
        self.env.failure_probability += falha_total
        if resultado:
            return resultado
        else:
            for service in services:
                service.route = None
                self.drop_service(service)
            return services

class ILP_without_probability_awareness(RestorationPolicy):
    def __init__(self, cont) -> None:
        super().__init__()
        self.name = 'ILP_PRwR'
        self.cont = cont
    
    def generate_ILP(self, services: Sequence['Service'], alpha:int):
        #print("ENTROU GENERATE ILP 1")
        #print("self.cont = ", self.cont)
        if not os.path.exists("arquivos_otimizacao_woc"):
            os.makedirs("arquivos_otimizacao_woc")
        nome = './arquivos_otimizacao_woc/gurobi_otimizacao' + '_'+ str(self.cont) +'_'+ str(alpha)+ "_" +str(int(self.env.current_time))+'.lp'
        #print("nome: ", nome)
        #print("nome: ", nome)
        sumNormalizedTime = 0
        normalizedRelocationTime = 0 
        normalizedRestorationTime = 0
        greaterRemainingTime = 0  
        usa_tempo = True
        for service in services:
            #print("service.remaining_time = ", service.remaining_time)
            if greaterRemainingTime < (service.holding_time - (self.env.current_time - service.arrival_time)):
                greaterRemainingTime = service.holding_time - self.env.current_time + service.arrival_time
        print("achou greaterRemainingTime: ", greaterRemainingTime)

        
        with open(nome, 'w') as lp:
            lp.write("Minimize wls + 1000 relocations  + 10000 unrestored_time \n") # diminui relocations de 1000 para 100
            #print("ENTROU GENERATE ILP 4")
           
        #   sujeito a:
            lp.write("Subject to\n")
            #print("flow conservation")
            #flow conservation
            for service in services:
                for node in self.env.topology.nodes():
                    first = True
                    if service.source == node:
                        for nb in list(self.env.topology.neighbors(node)):
                            link = self.env.topology[node][nb]
                            if link['current_failure_probability'] != 1:
                                if not first:
                                    lp.write(" + ")
                                else:
                                    first = False
                                lp.write("x_" + str(service.service_id) + "_" + str(link['id']))
                        lp.write(" - restored_" + str(service.service_id) + " = 0 \n")
                    elif self.env.topology.nodes[node]['dc']:
                        for nb in list(self.env.topology.neighbors(node)):
                            link = self.env.topology[node][nb]
                            if link['current_failure_probability'] != 1:
                                if not first:
                                    lp.write(" + ")
                                else:
                                    first = False
                                lp.write("x_" + str(service.service_id) + "_" + str(link['id']))
                        lp.write(" - restored_dc_" + str(service.service_id) + "_" + str(node)+ " = 0 \n")
                    elif node != service.source:
                        for nb in list(self.env.topology.neighbors(node)):
                            link = self.env.topology[node][nb]
                            if link['current_failure_probability'] != 1:
                                if not first:
                                    lp.write(" + ")
                                else:
                                    first = False
                                lp.write("x_" + str(service.service_id) + "_" + str(link['id']))
                        lp.write(" - 2 restored_node_" + str(service.service_id) + "_" + str(node) + " = 0 \n")
            #eq. 6 paper:
            #print("eq. 6 paper: ")
            for lnk in self.env.topology.edges():
                link = self.env.topology[lnk[0]][lnk[1]]
                if link['current_failure_probability'] != 1:
                    first = True
                    for service in services:
                        if not first:
                            lp.write(" + ")
                        else:
                            first = False
                        lp.write("x_" + str(service.service_id)+ "_" + str(link['id']))
                    lp.write(" - load_" + str(link['id']) + " = 0\n")
            #print("load <= available units")
            for lnk in self.env.topology.edges():
                link = self.env.topology[lnk[0]][lnk[1]]
                if link['current_failure_probability'] != 1:
                    lp.write("load_" + str(self.env.topology[lnk[0]][lnk[1]]['id']) + " <= " + str(self.env.topology[lnk[0]][lnk[1]]['available_units'])+"\n")
            #print("get required computing units")
            #get required computing units
            for node in self.env.topology.nodes():
                if self.env.topology.nodes[node]['dc']:
                    first = True
                    for service in services:
                        if not first:
                            lp.write(" + ")
                        else:
                            first = False
                        lp.write( str(service.computing_units) + " restore_dc_" + str(service.service_id) + "_" + str(node))
                    lp.write(" <= " + str(self.env.topology.nodes[node]['available_units']) + "\n")
            first = True
            total = 0
            #print("calcula as wavelengths utilizadas")
            #calcula as wavelengths utilizadas
            for lnk in self.env.topology.edges():
                link = self.env.topology[lnk[0]][lnk[1]]
                if link['current_failure_probability'] != 1:
                    total += link['available_units']
                    if not first:
                        lp.write(" + ")
                    else:
                        first = False
                    lp.write("load_" + str(link['id']))
            lp.write(" - wls = 0 \n")
            first = True
            #print("restored")
            for service in services:
                if not first:
                    lp.write(" + ")
                else:
                    first = False
                lp.write("restored_" + str(service.service_id))
            lp.write(" - restored = 0 \n")
            #print("serviços restaurados + não restaurados = total de serviços")
            #serviços restaurados + não restaurados = total de serviços
            lp.write("unrestored + restored = " + str(len(services))+ "\n")
            
            #print("serviço só pode ser restaurado em um DC")
            #serviço só pode ser restaurado em um DC
            for service in services:
                first = True
                for node in self.env.topology.nodes():
                    if self.env.topology.nodes[node]['dc']:
                        if not first:
                            lp.write(" + ")
                        else:
                            first = False
                        lp.write("restored_dc_" + str(service.service_id) + "_" + str(node))
                lp.write(" <= 1 \n")
            #se o serviço precisar ser realocado, só será realocado para um DC
            #print("#se o serviço precisar ser realocado, só será realocado para um DC")
            for service in services:
                first = True
                for node in self.env.topology.nodes():
                    #print("Entrou se realocado")
                    #print("service destination: ", service.destination)
                    #print("node: ", node)
                    if self.env.topology.nodes[node]['dc'] and node != service.destination:
                        if not first:
                            lp.write(" + ")
                        else:
                            lp.write("restored_dc_" + str(service.service_id) + "_" + str(node))
                        lp.write(" - relocation_" + str (service.service_id) + " = 0 \n")
            #calcula o numero de realocações realizadas
            #print("#calcula o numero de realocações realizadas")
            first = True
            for service in services:
                if not first:
                    lp.write(" + ")
                else:
                    first = False
                lp.write("relocation_" + str(service.service_id))
            lp.write(" - relocations = 0 \n")
            first = True
            factor = 10000
            lightSpeed = 300000
            #print("unrestored time")
            for service in services: 
                #print("entra services")
                for node in self.env.topology.nodes():
                    #print("entra nodes")
                    if self.env.topology.nodes[node]['dc']: #and node != service.destination: 
                        #print("if self.env.topology.nodes[node]['dc']:")
                        #print("(service.holding_time - (self.env.current_time - service.arrival_time)): ", (service.holding_time - (self.env.current_time - service.arrival_time)))
                        normalizedRemainingTime = int(math.ceil(factor * (service.arrival_time + service.holding_time - self.env.current_time)/(greaterRemainingTime)))
                        sumNormalizedTime += normalizedRemainingTime
                        if service.destination == node:
                            #print("if service.destination == node:")
                            if not first:
                                lp.write(" + ")
                            else:
                                first = False
                            lp.write(str(normalizedRemainingTime) + " restored_dc_" + str(service.service_id) + "_" + str(node))
                        else:
                            #print("else")
                            #relocation time: caminho mais rapido entre DCs distancia_total/velocidade_da_luz * factor
                            shortest_distance = nx.shortest_path_length(self.env.topology, source=service.source, target=node, weight='length')
                            relocationTime = float (shortest_distance/lightSpeed)
                            normalizedRelocationTime = int((relocationTime/greaterRemainingTime)*factor)
                            if normalizedRelocationTime < normalizedRemainingTime:
                                if not first:
                                    lp.write(" + ")
                                else:
                                    first = False
                                lp.write(str(normalizedRemainingTime - normalizedRelocationTime) + " restored_dc_" + str(service.service_id) + "_" + str(node))
            lp.write(" - restored_time = 0 \n")
            lp.write("unrestored_time + restored_time = " + str(sumNormalizedTime) + "\n")
            #print("binary")
            lp.write("Binary \n")
            for service in services:
                for node in self.env.topology.nodes():
                    if (not self.env.topology.nodes[node]['dc']) and node != service.destination and node != service.source:
                        lp.write("restored_node_" + str(service.service_id) + "_" + str(node) + "\n")
                    elif self.env.topology.nodes[node]['dc']:
                        lp.write("restored_dc_" + str(service.service_id) + "_" + str(node) + "\n")
                for lnk in self.env.topology.edges():
                    link = self.env.topology[lnk[0]][lnk[1]]

                    if link['current_failure_probability'] != 1:
                        lp.write("x_"+ str(service.service_id) + "_" + str(link['id']) + "\n")
                lp.write("restored_" + str(service.service_id) + "\n")
                lp.write("relocation_" + str(service.service_id) + "\n")
            #print("general")
            lp.write("General \n")
            for lnk in self.env.topology.edges():
                link = self.env.topology[lnk[0]][lnk[1]]
                if link['current_failure_probability'] != 1:
                    lp.write("load_" + str(link ['id']) + "\n")
                
            for service in services:
                lp.write("path_" + str(service.service_id) + "\n")

            lp.write("restored \n")
            lp.write("restored_time \n")
            lp.write("unrestored_time \n")
            lp.write("unrestored \n")
            lp.write("relocations \n")
            lp.write("total_cost \n")
            lp.write("wls \n")
            lp.write("END \n")
            print("SAIU GENERATE ILP")
        
    def restore(self, services: Sequence['Service']):
        print("ENTROU RESTORE ILP!!!")
        contador = 0
        acabou = False
        resultado: Sequence['Service'] = []
        total_hops = 0
        probabilidade_total = 0
        tempo = 0
        falha_total = 0
        services_queda: Sequence['Service'] = []
        #print("len dos serviços antes da organização: ", len(services))
        services = sorted(services, key=lambda x: x.arrival_time - (self.env.current_time - x.holding_time) , reverse=True)
        #print("len: ", len(services))
        #print("services: ", services)
        for service in services[:]:
            if (service.holding_time + service.arrival_time - self.env.current_time) < 1800.0:
                services.remove(service)
                services_queda.append(service)

        for service in services_queda:
            service.route = None
            self.drop_service(service)


        while services:
            #print("EXISTE SERVICES  ")
            svs = services[:80]
            #print("len svs: ", len(svs))
            #print("svs: ", svs)
            if not svs:
                break
            #print("dividiu svs em um batch de 80 services")
            services = services[80:]
            #print("pega os proximos 80 services")
            self.generate_ILP(svs, contador)
            #print("generate PLI")
        #print("SAIU RESTORE")
            import gurobipy as gp
            from gurobipy import GRB
            from graph import Path
            #print("Entrou na otimização")
            # Crie um objeto de modelo

            arq = './arquivos_otimizacao_woc/gurobi_otimizacao'+'_'+ str(self.cont) +'_' + str(contador) + "_" + str(int(self.env.current_time)) +'.lp'
            contador += 1
            # Crie um objeto de modelo
            model = gp.read(arq)
            model.setParam(GRB.Param.TimeLimit, 120)
            #model.setParam(GRB.Param.MIPGap, 0.0)  # Definir a tolerância do gap para 0 para resultados mais exatos
            #model.setParam(GRB.Param.IntegralityFocus, 1)  # Focar mais na integridade das variáveis

            # Otimize o modelo
            model.optimize()
            print("arquivo otimizado foi: " + arq)
            print("otimizou com sucesso! ")
            
            # Verifique o status da otimização print("não serviços nao podem ser restaurados")
            if model.Status == GRB.OPTIMAL or (model.Status == GRB.TIME_LIMIT and model.solCount > 0):   #se a solução for ótima ou achou uma solução dentro do tempo
                #total hops será o número de wls usadas:
                tempo += model.Runtime
                print("É ÓTIMO OU TEM UMA SOLUÇÃO")
                total_hops += model.getVarByName('wls').x
                #para cada serviço, verifique qual dc foi utilizado:              
                for service in svs:
                    total_length = 0
                    restaurado = False
                    path = []
                    for node in self.env.topology.nodes():
                        if self.env.topology.nodes[node]['dc']:
                            name = 'restored_dc_' + str(service.service_id) + '_' + str(node)
                            if model.getVarByName(name).x == 1: #foi achado o dc para o qual o serviço foi restaurado
                                #print("É POSSIVEL SER RESTAURADO")
                                if node != service.destination:
                                    #print("SERVIÇO REALOCADO")
                                    service.relocated = True
                                service.failed = False
                                failures_list = []
                                #finished = False
                                source = service.source
                                path.append(source)
                                found = False
                                while not found:
                                    #print("WHILE NOT FOUND")
                                    #print("arq: ", arq)
                                    #print("serviço: ", service.service_id)
                                    for nb in list(self.env.topology.neighbors(source)):
                                        link = self.env.topology[source][nb]
                                        if link['current_failure_probability'] != 1:
                                            st = 'x_' + str(service.service_id) + '_' + str(link['id'])
                                            valor = round(model.getVarByName(st).x)
                                            if valor == 1:
                                                if nb not in path:
                                                    path.append(nb)
                                                    source = nb
                                                    failures_list.append(1 - link['current_failure_probability'])
                                                    break
                                    if source == node:
                                        found = True           

                                #print("saiu do for")
                                failure = 1 
                                for f in failures_list:
                                    failure *= f
                                falha = 1 - failure
                                service.expected_risk = falha
                                falha_total += falha
                                restaurado = True
                                #print("ACHOU A FALHA ESPERADA")
                                break
                        
                    if not restaurado:
                        #print("NÃO É POSSÍVEL SER RESTAURADO")
                        service.route = None
                        self.drop_service(service)

                    else:
                        #print("ESTA CALCULANDO A LENGTH")
                        for i in range(len(path) - 1):
                            link = self.env.topology[path[i]][path[i + 1]]
                            total_length += link["length"]
                        #print("ACHOU A LENGTH")
                        new_path = Path(path,total_length)
                        service.route = new_path 
                        self.env.provision_service(service)        
                        #print("ACHOU O PATH")
                #print(f"Valor da função objetivo: {model.objVal}")  
            elif model.Status == GRB.TIME_LIMIT and model.solCount <= 0:
                #print("NÃO FOI ENCONTRADA UM PATH POIS ESTOUROU O TEMPO")
                for service in services:
                    service.route = None
                    self.drop_service(service)
            else:
                #print("Não foi encontrada uma solução ótima.")
                for service in svs:
                    
                    service.route = None
                    self.drop_service(service)
            if model.Status == GRB.TIME_LIMIT and model.solCount > 0:
                diretorio_log = "log_pli_woc"
                objective_bound = model.ObjBound
                mipgap = model.MIPGap
                if not os.path.exists(diretorio_log):
                    os.makedirs(diretorio_log)
                arquivo = os.path.join(diretorio_log, "log_pli_gurobi.txt")
                # Abre o arquivo (cria se não existir) e escreve a mensagem
                if os.path.exists(arquivo):
                    # Abre o arquivo em modo de acréscimo ('append')
                    with open(arquivo, 'a') as f:
                        f.write('model.Status == GRB.TIME_LIMIT and model.solCount > 0 in the arquive: ' + arq + "\n")
                        f.write("the bound is " + str(objective_bound) + "\n")
                        f.write("The MIPGap is "+ str(mipgap)+ "\n")
                else:
                    # Cria um novo arquivo e escreve a mensagem
                    with open(arquivo, 'w') as f:
                        f.write('model.Status == GRB.TIME_LIMIT and model.solCount > 0.\n')
                        f.write("the bound is " + str(objective_bound) + "\n")
                        f.write("The MIPGap is "+ str(mipgap)+ "\n")
            elif model.Status == GRB.TIME_LIMIT and model.solCount <= 0:
                diretorio_log = "log_pli_woc"
                objective_bound = model.ObjBound
                if not os.path.exists(diretorio_log):
                    os.makedirs(diretorio_log)
                arquivo = os.path.join(diretorio_log,"log_pli_gurobi_wrong.txt")
                # Abre o arquivo (cria se não existir) e escreve a mensagem
                if os.path.exists(arquivo):
                    # Abre o arquivo em modo de acréscimo ('append')
                    with open(arquivo, 'a') as f:
                        f.write('model.Status == GRB.TIME_LIMIT and model.solCount <= 0\n')
                else:
                    # Cria um novo arquivo e escreve a mensagem
                    with open(arquivo, 'w') as f:
                        f.write('model.Status == GRB.TIME_LIMIT and model.solCount <= 0\n')
            resultado.extend(svs)
            model.close()
            #print("ELE SAI DA EXECUÇÃO")
        resultado.extend(services_queda)
        self.env.restorability_time += tempo
        self.env.failure_probability += falha_total
        if resultado:
            return resultado
        else:
            for service in services:
                service.route = None
                self.drop_service(service)
            return services


class ILP_probability_awareness_with_higher_cost(RestorationPolicy):
    def __init__(self, cont) -> None:
        super().__init__()
        self.name = 'ILP_HC'
        self.cont = cont
    
    def generate_ILP(self, services: Sequence['Service'], alpha:int):
        #print("ENTROU GENERATE ILP 1")
        #print("self.cont = ", self.cont)
        if not os.path.exists("arquivos_otimizacao_whc"):
            os.makedirs("arquivos_otimizacao_whc")
        nome = './arquivos_otimizacao_whc/gurobi_otimizacao' + '_'+ str(self.cont) +'_'+ str(alpha)+ "_" +str(int(self.env.current_time))+'.lp'
        #print("nome: ", nome)
        #print("nome: ", nome)
        sumNormalizedTime = 0
        normalizedRelocationTime = 0 
        normalizedRestorationTime = 0
        greaterRemainingTime = 0  
        usa_tempo = True
        for service in services:
            #print("service.remaining_time = ", service.remaining_time)
            if greaterRemainingTime < (service.holding_time - (self.env.current_time - service.arrival_time)):
                greaterRemainingTime = service.holding_time - self.env.current_time + service.arrival_time
        print("achou greaterRemainingTime: ", greaterRemainingTime)

        
        with open(nome, 'w') as lp:
            lp.write("Minimize wls + 1000 relocations  + 10000 unrestored_time  + 100000 total_cost \n") # diminui relocations de 1000 para 100
            #print("ENTROU GENERATE ILP 4")
           
        #   sujeito a:
            lp.write("Subject to\n")
            #print("flow conservation")
            #flow conservation
            for service in services:
                for node in self.env.topology.nodes():
                    first = True
                    if service.source == node:
                        for nb in list(self.env.topology.neighbors(node)):
                            link = self.env.topology[node][nb]
                            if link['current_failure_probability'] != 1:
                                if not first:
                                    lp.write(" + ")
                                else:
                                    first = False
                                lp.write("x_" + str(service.service_id) + "_" + str(link['id']))
                        lp.write(" - restored_" + str(service.service_id) + " = 0 \n")
                    elif self.env.topology.nodes[node]['dc']:
                        for nb in list(self.env.topology.neighbors(node)):
                            link = self.env.topology[node][nb]
                            if link['current_failure_probability'] != 1:
                                if not first:
                                    lp.write(" + ")
                                else:
                                    first = False
                                lp.write("x_" + str(service.service_id) + "_" + str(link['id']))
                        lp.write(" - restored_dc_" + str(service.service_id) + "_" + str(node)+ " = 0 \n")
                    elif node != service.source:
                        for nb in list(self.env.topology.neighbors(node)):
                            link = self.env.topology[node][nb]
                            if link['current_failure_probability'] != 1:
                                if not first:
                                    lp.write(" + ")
                                else:
                                    first = False
                                lp.write("x_" + str(service.service_id) + "_" + str(link['id']))
                        lp.write(" - 2 restored_node_" + str(service.service_id) + "_" + str(node) + " = 0 \n")
            #eq. 6 paper:
            #print("eq. 6 paper: ")
            for lnk in self.env.topology.edges():
                link = self.env.topology[lnk[0]][lnk[1]]
                if link['current_failure_probability'] != 1:
                    first = True
                    for service in services:
                        if not first:
                            lp.write(" + ")
                        else:
                            first = False
                        lp.write("x_" + str(service.service_id)+ "_" + str(link['id']))
                    lp.write(" - load_" + str(link['id']) + " = 0\n")
            #print("load <= available units")
            for lnk in self.env.topology.edges():
                link = self.env.topology[lnk[0]][lnk[1]]
                if link['current_failure_probability'] != 1:
                    lp.write("load_" + str(self.env.topology[lnk[0]][lnk[1]]['id']) + " <= " + str(self.env.topology[lnk[0]][lnk[1]]['available_units'])+"\n")
            #print("get required computing units")
            #get required computing units
            for node in self.env.topology.nodes():
                if self.env.topology.nodes[node]['dc']:
                    first = True
                    for service in services:
                        if not first:
                            lp.write(" + ")
                        else:
                            first = False
                        lp.write( str(service.computing_units) + " restore_dc_" + str(service.service_id) + "_" + str(node))
                    lp.write(" <= " + str(self.env.topology.nodes[node]['available_units']) + "\n")
            first = True
            total = 0
            #print("calcula as wavelengths utilizadas")
            #calcula as wavelengths utilizadas
            for lnk in self.env.topology.edges():
                link = self.env.topology[lnk[0]][lnk[1]]
                if link['current_failure_probability'] != 1:
                    total += link['available_units']
                    if not first:
                        lp.write(" + ")
                    else:
                        first = False
                    lp.write("load_" + str(link['id']))
            lp.write(" - wls = 0 \n")
            first = True
            #print("restored")
            for service in services:
                if not first:
                    lp.write(" + ")
                else:
                    first = False
                lp.write("restored_" + str(service.service_id))
            lp.write(" - restored = 0 \n")
            #print("serviços restaurados + não restaurados = total de serviços")
            #serviços restaurados + não restaurados = total de serviços
            lp.write("unrestored + restored = " + str(len(services))+ "\n")
            
            #print("serviço só pode ser restaurado em um DC")
            #serviço só pode ser restaurado em um DC
            for service in services:
                first = True
                for node in self.env.topology.nodes():
                    if self.env.topology.nodes[node]['dc']:
                        if not first:
                            lp.write(" + ")
                        else:
                            first = False
                        lp.write("restored_dc_" + str(service.service_id) + "_" + str(node))
                lp.write(" <= 1 \n")
            #se o serviço precisar ser realocado, só será realocado para um DC
            #print("#se o serviço precisar ser realocado, só será realocado para um DC")
            for service in services:
                first = True
                for node in self.env.topology.nodes():
                    #print("Entrou se realocado")
                    #print("service destination: ", service.destination)
                    #print("node: ", node)
                    if self.env.topology.nodes[node]['dc'] and node != service.destination:
                        if not first:
                            lp.write(" + ")
                        else:
                            lp.write("restored_dc_" + str(service.service_id) + "_" + str(node))
                        lp.write(" - relocation_" + str (service.service_id) + " = 0 \n")
            #calcula o numero de realocações realizadas
            #print("#calcula o numero de realocações realizadas")
            first = True
            for service in services:
                if not first:
                    lp.write(" + ")
                else:
                    first = False
                lp.write("relocation_" + str(service.service_id))
            lp.write(" - relocations = 0 \n")
            #print("total_cost")
            first = True
            for service in services:
                if not first:
                    lp.write(" + ")
                else:
                    first = False
                lp.write("path_" + str(service.service_id))
            lp.write(" - total_cost = 0\n")
            #print("probability")
            for service in services:
                first = True
                for lnk in self.env.topology.edges():
                    link = self.env.topology[lnk[0]][lnk[1]]
                    if link['current_failure_probability'] != 1:
                        if not first:
                            lp.write(" + ")
                        else:
                            first = False
                        #print("entrou failure probability")
                        
                        if link['current_failure_probability'] == 0:
                            ln_prob = 1
                        else:
                            ln_prob = round(math.log(1 - link['current_failure_probability']), 2) * (-100)
                        lp.write(" " + str(ln_prob) + " x_" + str(service.service_id) + "_" + str(link['id']))
                    
                lp.write(" - path_" + str(service.service_id) + " = 0\n")
            first = True
            factor = 10000
            lightSpeed = 300000
            #print("unrestored time")
            for service in services: 
                #print("entra services")
                for node in self.env.topology.nodes():
                    #print("entra nodes")
                    if self.env.topology.nodes[node]['dc']: #and node != service.destination: 
                        #print("if self.env.topology.nodes[node]['dc']:")
                        #print("(service.holding_time - (self.env.current_time - service.arrival_time)): ", (service.holding_time - (self.env.current_time - service.arrival_time)))
                        normalizedRemainingTime = int(math.ceil(factor * (service.arrival_time + service.holding_time - self.env.current_time)/(greaterRemainingTime)))
                        sumNormalizedTime += normalizedRemainingTime
                        if service.destination == node:
                            #print("if service.destination == node:")
                            if not first:
                                lp.write(" + ")
                            else:
                                first = False
                            lp.write(str(normalizedRemainingTime) + " restored_dc_" + str(service.service_id) + "_" + str(node))
                        else:
                            #print("else")
                            #relocation time: caminho mais rapido entre DCs distancia_total/velocidade_da_luz * factor
                            shortest_distance = nx.shortest_path_length(self.env.topology, source=service.source, target=node, weight='length')
                            relocationTime = float (shortest_distance/lightSpeed)
                            normalizedRelocationTime = int((relocationTime/greaterRemainingTime)*factor)
                            if normalizedRelocationTime < normalizedRemainingTime:
                                if not first:
                                    lp.write(" + ")
                                else:
                                    first = False
                                lp.write(str(normalizedRemainingTime - normalizedRelocationTime) + " restored_dc_" + str(service.service_id) + "_" + str(node))
            lp.write(" - restored_time = 0 \n")
            lp.write("unrestored_time + restored_time = " + str(sumNormalizedTime) + "\n")
            #print("binary")
            lp.write("Binary \n")
            for service in services:
                for node in self.env.topology.nodes():
                    if (not self.env.topology.nodes[node]['dc']) and node != service.destination and node != service.source:
                        lp.write("restored_node_" + str(service.service_id) + "_" + str(node) + "\n")
                    elif self.env.topology.nodes[node]['dc']:
                        lp.write("restored_dc_" + str(service.service_id) + "_" + str(node) + "\n")
                for lnk in self.env.topology.edges():
                    link = self.env.topology[lnk[0]][lnk[1]]

                    if link['current_failure_probability'] != 1:
                        lp.write("x_"+ str(service.service_id) + "_" + str(link['id']) + "\n")
                lp.write("restored_" + str(service.service_id) + "\n")
                lp.write("relocation_" + str(service.service_id) + "\n")
            #print("general")
            lp.write("General \n")
            for lnk in self.env.topology.edges():
                link = self.env.topology[lnk[0]][lnk[1]]
                if link['current_failure_probability'] != 1:
                    lp.write("load_" + str(link ['id']) + "\n")
                
            for service in services:
                lp.write("path_" + str(service.service_id) + "\n")

            lp.write("restored \n")
            lp.write("restored_time \n")
            lp.write("unrestored_time \n")
            lp.write("unrestored \n")
            lp.write("relocations \n")
            lp.write("total_cost \n")
            lp.write("wls \n")
            lp.write("END \n")
            print("SAIU GENERATE ILP")
        
    def restore(self, services: Sequence['Service']):
        print("ENTROU RESTORE ILP!!!")
        contador = 0
        acabou = False
        resultado: Sequence['Service'] = []
        total_hops = 0
        probabilidade_total = 0
        tempo = 0
        falha_total = 0
        services_queda: Sequence['Service'] = []
        #print("len dos serviços antes da organização: ", len(services))
        services = sorted(services, key=lambda x: x.arrival_time - (self.env.current_time - x.holding_time) , reverse=True)
        #print("len: ", len(services))
        #print("services: ", services)
        for service in services[:]:
            if (service.holding_time + service.arrival_time - self.env.current_time) < 1800.0:
                services.remove(service)
                services_queda.append(service)

        for service in services_queda:
            service.route = None
            self.drop_service(service)


        while services:
            #print("EXISTE SERVICES  ")
            svs = services[:80]
            #print("len svs: ", len(svs))
            #print("svs: ", svs)
            if not svs:
                break
            #print("dividiu svs em um batch de 80 services")
            services = services[80:]
            #print("pega os proximos 80 services")
            self.generate_ILP(svs, contador)
            #print("generate PLI")
        #print("SAIU RESTORE")
            import gurobipy as gp
            from gurobipy import GRB
            from graph import Path
            #print("Entrou na otimização")
            # Crie um objeto de modelo

            arq = './arquivos_otimizacao_whc/gurobi_otimizacao'+'_'+ str(self.cont) +'_' + str(contador) + "_" + str(int(self.env.current_time)) +'.lp'
            contador += 1
            # Crie um objeto de modelo
            model = gp.read(arq)
            model.setParam(GRB.Param.TimeLimit, 120)
            #model.setParam(GRB.Param.MIPGap, 0.0)  # Definir a tolerância do gap para 0 para resultados mais exatos
            #model.setParam(GRB.Param.IntegralityFocus, 1)  # Focar mais na integridade das variáveis

            # Otimize o modelo
            model.optimize()
            print("arquivo otimizado foi: " + arq)
            print("otimizou com sucesso! ")
            
            # Verifique o status da otimização print("não serviços nao podem ser restaurados")
            if model.Status == GRB.OPTIMAL or (model.Status == GRB.TIME_LIMIT and model.solCount > 0):   #se a solução for ótima ou achou uma solução dentro do tempo
                #total hops será o número de wls usadas:
                tempo += model.Runtime
                print("É ÓTIMO OU TEM UMA SOLUÇÃO")
                total_hops += model.getVarByName('wls').x
                #para cada serviço, verifique qual dc foi utilizado:              
                for service in svs:
                    total_length = 0
                    restaurado = False
                    path = []
                    for node in self.env.topology.nodes():
                        if self.env.topology.nodes[node]['dc']:
                            name = 'restored_dc_' + str(service.service_id) + '_' + str(node)
                            if model.getVarByName(name).x == 1: #foi achado o dc para o qual o serviço foi restaurado
                                #print("É POSSIVEL SER RESTAURADO")
                                if node != service.destination:
                                    #print("SERVIÇO REALOCADO")
                                    service.relocated = True
                                service.failed = False
                                failures_list = []
                                #finished = False
                                source = service.source
                                path.append(source)
                                found = False
                                while not found:
                                    #print("WHILE NOT FOUND")
                                    #print("arq: ", arq)
                                    #print("serviço: ", service.service_id)
                                    for nb in list(self.env.topology.neighbors(source)):
                                        link = self.env.topology[source][nb]
                                        if link['current_failure_probability'] != 1:
                                            st = 'x_' + str(service.service_id) + '_' + str(link['id'])
                                            valor = round(model.getVarByName(st).x)
                                            if valor == 1:
                                                if nb not in path:
                                                    path.append(nb)
                                                    source = nb
                                                    failures_list.append(1 - link['current_failure_probability'])
                                                    break
                                    if source == node:
                                        found = True           

                                #print("saiu do for")
                                failure = 1 
                                for f in failures_list:
                                    failure *= f
                                falha = 1 - failure
                                service.expected_risk = falha
                                falha_total += falha
                                restaurado = True
                                #print("ACHOU A FALHA ESPERADA")
                                break
                        
                    if not restaurado:
                        #print("NÃO É POSSÍVEL SER RESTAURADO")
                        service.route = None
                        self.drop_service(service)

                    else:
                        #print("ESTA CALCULANDO A LENGTH")
                        for i in range(len(path) - 1):
                            link = self.env.topology[path[i]][path[i + 1]]
                            total_length += link["length"]
                        #print("ACHOU A LENGTH")
                        new_path = Path(path,total_length)
                        service.route = new_path 
                        self.env.provision_service(service)        
                        #print("ACHOU O PATH")
                #print(f"Valor da função objetivo: {model.objVal}")  
            elif model.Status == GRB.TIME_LIMIT and model.solCount <= 0:
                #print("NÃO FOI ENCONTRADA UM PATH POIS ESTOUROU O TEMPO")
                for service in services:
                    service.route = None
                    self.drop_service(service)
            else:
                #print("Não foi encontrada uma solução ótima.")
                for service in svs:
                    
                    service.route = None
                    self.drop_service(service)
            if model.Status == GRB.TIME_LIMIT and model.solCount > 0:
                diretorio_log = "log_pli_HC"
                objective_bound = model.ObjBound
                mipgap = model.MIPGap
                if not os.path.exists(diretorio_log):
                    os.makedirs(diretorio_log)
                arquivo = os.path.join(diretorio_log, "log_pli_gurobi.txt")
                if os.path.exists(arquivo):
                    # Abre o arquivo em modo de acréscimo ('append')
                    with open(arquivo, 'a') as f:
                        f.write('model.Status == GRB.TIME_LIMIT and model.solCount > 0in the arquive: ' + arq + "\n")
                        f.write("the bound is " + str(objective_bound) + "\n")
                        f.write("The MIPGap is "+ str(mipgap)+ "\n")
                else:
                    # Cria um novo arquivo e escreve a mensagem
                    with open(arquivo, 'w') as f:
                        f.write('model.Status == GRB.TIME_LIMIT and model.solCount > 0.\n')
                        f.write("the bound is " + str(objective_bound) + "\n")
                        f.write("The MIPGap is "+ str(mipgap)+ "\n")
            elif model.Status == GRB.TIME_LIMIT and model.solCount <= 0:
                diretorio_log = "log_pli_HC"
                objective_bound = model.ObjBound
                if not os.path.exists(diretorio_log):
                    os.makedirs(diretorio_log)
                arquivo = os.path.join(diretorio_log,"log_pli_gurobi_wrong.txt")
                # Abre o arquivo (cria se não existir) e escreve a mensagem
                if os.path.exists(arquivo):
                    # Abre o arquivo em modo de acréscimo ('append')
                    with open(arquivo, 'a') as f:
                        f.write('model.Status == GRB.TIME_LIMIT and model.solCount <= 0\n')
                else:
                    # Cria um novo arquivo e escreve a mensagem
                    with open(arquivo, 'w') as f:
                        f.write('model.Status == GRB.TIME_LIMIT and model.solCount <= 0\n')
            resultado.extend(svs)
            model.close()
            #print("ELE SAI DA EXECUÇÃO")
        resultado.extend(services_queda)
        self.env.restorability_time += tempo
        self.env.failure_probability += falha_total
        if resultado:
            return resultado
        else:
            for service in services:
                service.route = None
                self.drop_service(service)
            return services

class ILP_probability_awareness_with_higher_ut(RestorationPolicy):
    def __init__(self, cont) -> None:
        super().__init__()
        self.name = 'ILP_whut'
        self.cont = cont
    
    def generate_ILP(self, services: Sequence['Service'], alpha:int):
        #print("ENTROU GENERATE ILP 1")
        #print("self.cont = ", self.cont)
        if not os.path.exists("arquivos_otimizacao_whut"):
            os.makedirs("arquivos_otimizacao_whut")
        nome = './arquivos_otimizacao_whut/gurobi_otimizacao' + '_'+ str(self.cont) +'_'+ str(alpha)+ "_" +str(int(self.env.current_time))+'.lp'
        #print("nome: ", nome)
        #print("nome: ", nome)
        sumNormalizedTime = 0
        normalizedRelocationTime = 0 
        normalizedRestorationTime = 0
        greaterRemainingTime = 0  
        usa_tempo = True
        for service in services:
            #print("service.remaining_time = ", service.remaining_time)
            if greaterRemainingTime < (service.holding_time - (self.env.current_time - service.arrival_time)):
                greaterRemainingTime = service.holding_time - self.env.current_time + service.arrival_time
        print("achou greaterRemainingTime: ", greaterRemainingTime)

        
        with open(nome, 'w') as lp:
            lp.write("Minimize wls + 1000 relocations  + 100000 unrestored_time  + 10000 total_cost \n")
            #print("ENTROU GENERATE ILP 4")
           
        #   sujeito a:
            lp.write("Subject to\n")
            #print("flow conservation")
            #flow conservation
            for service in services:
                for node in self.env.topology.nodes():
                    first = True
                    if service.source == node:
                        for nb in list(self.env.topology.neighbors(node)):
                            link = self.env.topology[node][nb]
                            if link['current_failure_probability'] != 1:
                                if not first:
                                    lp.write(" + ")
                                else:
                                    first = False
                                lp.write("x_" + str(service.service_id) + "_" + str(link['id']))
                        lp.write(" - restored_" + str(service.service_id) + " = 0 \n")
                    elif self.env.topology.nodes[node]['dc']:
                        for nb in list(self.env.topology.neighbors(node)):
                            link = self.env.topology[node][nb]
                            if link['current_failure_probability'] != 1:
                                if not first:
                                    lp.write(" + ")
                                else:
                                    first = False
                                lp.write("x_" + str(service.service_id) + "_" + str(link['id']))
                        lp.write(" - restored_dc_" + str(service.service_id) + "_" + str(node)+ " = 0 \n")
                    elif node != service.source:
                        for nb in list(self.env.topology.neighbors(node)):
                            link = self.env.topology[node][nb]
                            if link['current_failure_probability'] != 1:
                                if not first:
                                    lp.write(" + ")
                                else:
                                    first = False
                                lp.write("x_" + str(service.service_id) + "_" + str(link['id']))
                        lp.write(" - 2 restored_node_" + str(service.service_id) + "_" + str(node) + " = 0 \n")
            #eq. 6 paper:
            #print("eq. 6 paper: ")
            for lnk in self.env.topology.edges():
                link = self.env.topology[lnk[0]][lnk[1]]
                if link['current_failure_probability'] != 1:
                    first = True
                    for service in services:
                        if not first:
                            lp.write(" + ")
                        else:
                            first = False
                        lp.write("x_" + str(service.service_id)+ "_" + str(link['id']))
                    lp.write(" - load_" + str(link['id']) + " = 0\n")
            #print("load <= available units")
            for lnk in self.env.topology.edges():
                link = self.env.topology[lnk[0]][lnk[1]]
                if link['current_failure_probability'] != 1:
                    lp.write("load_" + str(self.env.topology[lnk[0]][lnk[1]]['id']) + " <= " + str(self.env.topology[lnk[0]][lnk[1]]['available_units'])+"\n")
            #print("get required computing units")
            #get required computing units
            for node in self.env.topology.nodes():
                if self.env.topology.nodes[node]['dc']:
                    first = True
                    for service in services:
                        if not first:
                            lp.write(" + ")
                        else:
                            first = False
                        lp.write( str(service.computing_units) + " restore_dc_" + str(service.service_id) + "_" + str(node))
                    lp.write(" <= " + str(self.env.topology.nodes[node]['available_units']) + "\n")
            first = True
            total = 0
            #print("calcula as wavelengths utilizadas")
            #calcula as wavelengths utilizadas
            for lnk in self.env.topology.edges():
                link = self.env.topology[lnk[0]][lnk[1]]
                if link['current_failure_probability'] != 1:
                    total += link['available_units']
                    if not first:
                        lp.write(" + ")
                    else:
                        first = False
                    lp.write("load_" + str(link['id']))
            lp.write(" - wls = 0 \n")
            first = True
            #print("restored")
            for service in services:
                if not first:
                    lp.write(" + ")
                else:
                    first = False
                lp.write("restored_" + str(service.service_id))
            lp.write(" - restored = 0 \n")
            #print("serviços restaurados + não restaurados = total de serviços")
            #serviços restaurados + não restaurados = total de serviços
            lp.write("unrestored + restored = " + str(len(services))+ "\n")
            
            #print("serviço só pode ser restaurado em um DC")
            #serviço só pode ser restaurado em um DC
            for service in services:
                first = True
                for node in self.env.topology.nodes():
                    if self.env.topology.nodes[node]['dc']:
                        if not first:
                            lp.write(" + ")
                        else:
                            first = False
                        lp.write("restored_dc_" + str(service.service_id) + "_" + str(node))
                lp.write(" <= 1 \n")
            #se o serviço precisar ser realocado, só será realocado para um DC
            #print("#se o serviço precisar ser realocado, só será realocado para um DC")
            for service in services:
                first = True
                for node in self.env.topology.nodes():
                    #print("Entrou se realocado")
                    #print("service destination: ", service.destination)
                    #print("node: ", node)
                    if self.env.topology.nodes[node]['dc'] and node != service.destination:
                        if not first:
                            lp.write(" + ")
                        else:
                            lp.write("restored_dc_" + str(service.service_id) + "_" + str(node))
                        lp.write(" - relocation_" + str (service.service_id) + " = 0 \n")
            #calcula o numero de realocações realizadas
            #print("#calcula o numero de realocações realizadas")
            first = True
            for service in services:
                if not first:
                    lp.write(" + ")
                else:
                    first = False
                lp.write("relocation_" + str(service.service_id))
            lp.write(" - relocations = 0 \n")
            #print("total_cost")
            first = True
            for service in services:
                if not first:
                    lp.write(" + ")
                else:
                    first = False
                lp.write("path_" + str(service.service_id))
            lp.write(" - total_cost = 0\n")
            #print("probability")
            for service in services:
                first = True
                for lnk in self.env.topology.edges():
                    link = self.env.topology[lnk[0]][lnk[1]]
                    if link['current_failure_probability'] != 1:
                        if not first:
                            lp.write(" + ")
                        else:
                            first = False
                        #print("entrou failure probability")
                        
                        if link['current_failure_probability'] == 0:
                            ln_prob = 1
                        else:
                            ln_prob = round(math.log(1 - link['current_failure_probability']), 2) * (-100)
                        lp.write(" " + str(ln_prob) + " x_" + str(service.service_id) + "_" + str(link['id']))
                    
                lp.write(" - path_" + str(service.service_id) + " = 0\n")
            first = True
            factor = 10000
            lightSpeed = 300000
            #print("unrestored time")
            for service in services: 
                #print("entra services")
                for node in self.env.topology.nodes():
                    #print("entra nodes")
                    if self.env.topology.nodes[node]['dc']: #and node != service.destination: 
                        #print("if self.env.topology.nodes[node]['dc']:")
                        #print("(service.holding_time - (self.env.current_time - service.arrival_time)): ", (service.holding_time - (self.env.current_time - service.arrival_time)))
                        normalizedRemainingTime = int(math.ceil(factor * (service.arrival_time + service.holding_time - self.env.current_time)/(greaterRemainingTime)))
                        sumNormalizedTime += normalizedRemainingTime
                        if service.destination == node:
                            #print("if service.destination == node:")
                            if not first:
                                lp.write(" + ")
                            else:
                                first = False
                            lp.write(str(normalizedRemainingTime) + " restored_dc_" + str(service.service_id) + "_" + str(node))
                        else:
                            #print("else")
                            #relocation time: caminho mais rapido entre DCs distancia_total/velocidade_da_luz * factor
                            shortest_distance = nx.shortest_path_length(self.env.topology, source=service.source, target=node, weight='length')
                            relocationTime = float (shortest_distance/lightSpeed)
                            normalizedRelocationTime = int((relocationTime/greaterRemainingTime)*factor)
                            if normalizedRelocationTime < normalizedRemainingTime:
                                if not first:
                                    lp.write(" + ")
                                else:
                                    first = False
                                lp.write(str(normalizedRemainingTime - normalizedRelocationTime) + " restored_dc_" + str(service.service_id) + "_" + str(node))
            lp.write(" - restored_time = 0 \n")
            lp.write("unrestored_time + restored_time = " + str(sumNormalizedTime) + "\n")
            #print("binary")
            lp.write("Binary \n")
            for service in services:
                for node in self.env.topology.nodes():
                    if (not self.env.topology.nodes[node]['dc']) and node != service.destination and node != service.source:
                        lp.write("restored_node_" + str(service.service_id) + "_" + str(node) + "\n")
                    elif self.env.topology.nodes[node]['dc']:
                        lp.write("restored_dc_" + str(service.service_id) + "_" + str(node) + "\n")
                for lnk in self.env.topology.edges():
                    link = self.env.topology[lnk[0]][lnk[1]]

                    if link['current_failure_probability'] != 1:
                        lp.write("x_"+ str(service.service_id) + "_" + str(link['id']) + "\n")
                lp.write("restored_" + str(service.service_id) + "\n")
                lp.write("relocation_" + str(service.service_id) + "\n")
            #print("general")
            lp.write("General \n")
            for lnk in self.env.topology.edges():
                link = self.env.topology[lnk[0]][lnk[1]]
                if link['current_failure_probability'] != 1:
                    lp.write("load_" + str(link ['id']) + "\n")
                
            for service in services:
                lp.write("path_" + str(service.service_id) + "\n")

            lp.write("restored \n")
            lp.write("restored_time \n")
            lp.write("unrestored_time \n")
            lp.write("unrestored \n")
            lp.write("relocations \n")
            lp.write("total_cost \n")
            lp.write("wls \n")
            lp.write("END \n")
            print("SAIU GENERATE ILP")
        
    def restore(self, services: Sequence['Service']):
        print("ENTROU RESTORE ILP!!!")
        contador = 0
        acabou = False
        resultado: Sequence['Service'] = []
        total_hops = 0
        probabilidade_total = 0
        tempo = 0
        falha_total = 0
        services_queda: Sequence['Service'] = []
        #print("len dos serviços antes da organização: ", len(services))
        services = sorted(services, key=lambda x: x.arrival_time - (self.env.current_time - x.holding_time) , reverse=True)
        #print("len: ", len(services))
        #print("services: ", services)
        for service in services[:]:
            if (service.holding_time + service.arrival_time - self.env.current_time) < 1800.0:
                services.remove(service)
                services_queda.append(service)

        for service in services_queda:
            service.route = None
            self.drop_service(service)


        while services:
            #print("EXISTE SERVICES  ")
            svs = services[:80]
            #print("len svs: ", len(svs))
            #print("svs: ", svs)
            if not svs:
                break
            #print("dividiu svs em um batch de 80 services")
            services = services[80:]
            #print("pega os proximos 80 services")
            self.generate_ILP(svs, contador)
            #print("generate PLI")
        #print("SAIU RESTORE")
            import gurobipy as gp
            from gurobipy import GRB
            from graph import Path
            #print("Entrou na otimização")
            # Crie um objeto de modelo

            arq = './arquivos_otimizacao_whut/gurobi_otimizacao'+'_'+ str(self.cont) +'_' + str(contador) + "_" + str(int(self.env.current_time)) +'.lp'
            contador += 1
            # Crie um objeto de modelo
            model = gp.read(arq)
            model.setParam(GRB.Param.TimeLimit, 120)
            #model.setParam(GRB.Param.MIPGap, 0.0)  # Definir a tolerância do gap para 0 para resultados mais exatos
            #model.setParam(GRB.Param.IntegralityFocus, 1)  # Focar mais na integridade das variáveis

            # Otimize o modelo
            model.optimize()
            print("arquivo otimizado foi: " + arq)
            print("otimizou com sucesso! ")
            
            # Verifique o status da otimização print("não serviços nao podem ser restaurados")
            if model.Status == GRB.OPTIMAL or (model.Status == GRB.TIME_LIMIT and model.solCount > 0):   #se a solução for ótima ou achou uma solução dentro do tempo
                #total hops será o número de wls usadas:
                tempo += model.Runtime
                print("É ÓTIMO OU TEM UMA SOLUÇÃO")
                total_hops += model.getVarByName('wls').x
                #para cada serviço, verifique qual dc foi utilizado:              
                for service in svs:
                    total_length = 0
                    restaurado = False
                    path = []
                    for node in self.env.topology.nodes():
                        if self.env.topology.nodes[node]['dc']:
                            name = 'restored_dc_' + str(service.service_id) + '_' + str(node)
                            if model.getVarByName(name).x == 1: #foi achado o dc para o qual o serviço foi restaurado
                                #print("É POSSIVEL SER RESTAURADO")
                                if node != service.destination:
                                    #print("SERVIÇO REALOCADO")
                                    service.relocated = True
                                service.failed = False
                                failures_list = []
                                #finished = False
                                source = service.source
                                path.append(source)
                                found = False
                                while not found:
                                    #print("WHILE NOT FOUND")
                                    #print("arq: ", arq)
                                    #print("serviço: ", service.service_id)
                                    for nb in list(self.env.topology.neighbors(source)):
                                        link = self.env.topology[source][nb]
                                        if link['current_failure_probability'] != 1:
                                            st = 'x_' + str(service.service_id) + '_' + str(link['id'])
                                            valor = round(model.getVarByName(st).x)
                                            if valor == 1:
                                                if nb not in path:
                                                    path.append(nb)
                                                    source = nb
                                                    failures_list.append(1 - link['current_failure_probability'])
                                                    break
                                    if source == node:
                                        found = True           

                                #print("saiu do for")
                                failure = 1 
                                for f in failures_list:
                                    failure *= f
                                falha = 1 - failure
                                service.expected_risk = falha
                                falha_total += falha
                                restaurado = True
                                #print("ACHOU A FALHA ESPERADA")
                                break
                        
                    if not restaurado:
                        #print("NÃO É POSSÍVEL SER RESTAURADO")
                        service.route = None
                        self.drop_service(service)

                    else:
                        #print("ESTA CALCULANDO A LENGTH")
                        for i in range(len(path) - 1):
                            link = self.env.topology[path[i]][path[i + 1]]
                            total_length += link["length"]
                        #print("ACHOU A LENGTH")
                        new_path = Path(path,total_length)
                        service.route = new_path 
                        self.env.provision_service(service)        
                        #print("ACHOU O PATH")
                #print(f"Valor da função objetivo: {model.objVal}")  
            elif model.Status == GRB.TIME_LIMIT and model.solCount <= 0:
                #print("NÃO FOI ENCONTRADA UM PATH POIS ESTOUROU O TEMPO")
                for service in services:
                    service.route = None
                    self.drop_service(service)
            else:
                #print("Não foi encontrada uma solução ótima.")
                for service in svs:
                    
                    service.route = None
                    self.drop_service(service)
            if model.Status == GRB.TIME_LIMIT and model.solCount > 0:
                diretorio_log = "log_pli"
                objective_bound = model.ObjBound
                if not os.path.exists(diretorio_log):
                    os.makedirs(diretorio_log)
                arquivo = "log_pli_gurobi.txt"
                # Abre o arquivo (cria se não existir) e escreve a mensagem
                if os.path.exists(arquivo):
                    # Abre o arquivo em modo de acréscimo ('append')
                    with open(arquivo, 'a') as f:
                        f.write('model.Status == GRB.TIME_LIMIT and model.solCount > 0.\n' + "in the arquive: " + arq)
                        f.write("the bound is " + str(objective_bound) + "\n")
                else:
                    # Cria um novo arquivo e escreve a mensagem
                    with open(arquivo, 'w') as f:
                        f.write('model.Status == GRB.TIME_LIMIT and model.solCount > 0.\n')
                        f.write("the bound is " + str(objective_bound) + "\n")
            elif model.Status == GRB.TIME_LIMIT and model.solCount <= 0:
                diretorio_log = "log_pli"
                objective_bound = model.ObjBound
                mipgap = model.MIPGap
                if not os.path.exists(diretorio_log):
                    os.makedirs(diretorio_log)
                arquivo = "log_pli_gurobi.txt"
                # Abre o arquivo (cria se não existir) e escreve a mensagem
                if os.path.exists(arquivo):
                    # Abre o arquivo em modo de acréscimo ('append')
                    with open(arquivo, 'a') as f:
                        f.write('model.Status == GRB.TIME_LIMIT and model.solCount <= 0\n')
                else:
                    # Cria um novo arquivo e escreve a mensagem
                    with open(arquivo, 'w') as f:
                        f.write('model.Status == GRB.TIME_LIMIT and model.solCount <= 0\n')
            resultado.extend(svs)
            model.close()
            #print("ELE SAI DA EXECUÇÃO")
        resultado.extend(services_queda)
        self.env.restorability_time += tempo
        self.env.failure_probability += falha_total
        if resultado:
            return resultado
        else:
            for service in services:
                service.route = None
                self.drop_service(service)
            return services