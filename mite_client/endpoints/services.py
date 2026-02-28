from typing import List, Optional

from ..models import Service
from ..utils import build_query_params


class ServicesEndpoint:
    def __init__(self, client):
        self.client = client
    
    def list(self, archived: bool = False, **kwargs) -> List[Service]:
        endpoint = 'services/archived.json' if archived else 'services.json'
        params = build_query_params(**kwargs)
        
        response = self.client.get(endpoint, params=params)
        
        services = []
        for item in response:
            services.append(Service.from_dict(item))
        
        return services
    
    def get(self, service_id: int) -> Service:
        response = self.client.get(f'services/{service_id}.json')
        return Service.from_dict(response)
    
    def create(self, name: str, note: Optional[str] = None, hourly_rate: Optional[float] = None,
               billable: bool = True) -> Service:
        data = {
            'service': {
                'name': name,
                'billable': billable
            }
        }
        
        if note:
            data['service']['note'] = note
        if hourly_rate:
            data['service']['hourly-rate'] = hourly_rate
        
        response = self.client.post('services.json', data)
        return Service.from_dict(response)
    
    def update(self, service_id: int, **kwargs) -> Service:
        data = {'service': {}}
        
        field_mapping = {
            'name': 'name',
            'note': 'note',
            'hourly_rate': 'hourly-rate',
            'billable': 'billable',
            'archived': 'archived'
        }
        
        for key, value in kwargs.items():
            if key in field_mapping and value is not None:
                api_key = field_mapping[key]
                data['service'][api_key] = value
        
        response = self.client.patch(f'services/{service_id}.json', data)
        return Service.from_dict(response)
    
    def delete(self, service_id: int) -> bool:
        return self.client.delete(f'services/{service_id}.json')
    
    def get_active(self) -> List[Service]:
        return self.list(archived=False)
    
    def get_archived(self) -> List[Service]:
        return self.list(archived=True)
    
    def get_billable(self, archived: bool = False) -> List[Service]:
        all_services = self.list(archived=archived)
        return [s for s in all_services if s.billable]
    
    def get_non_billable(self, archived: bool = False) -> List[Service]:
        all_services = self.list(archived=archived)
        return [s for s in all_services if not s.billable]
    
    def search_by_name(self, name: str, archived: bool = False) -> List[Service]:
        return self.list(name=name, archived=archived)
    
    def archive(self, service_id: int) -> Service:
        return self.update(service_id, archived=True)
    
    def unarchive(self, service_id: int) -> Service:
        return self.update(service_id, archived=False)