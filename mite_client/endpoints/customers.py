from typing import List, Optional

from ..models import Customer
from ..utils import build_query_params


class CustomersEndpoint:
    def __init__(self, client):
        self.client = client
    
    def list(self, archived: bool = False, **kwargs) -> List[Customer]:
        endpoint = 'customers/archived.json' if archived else 'customers.json'
        params = build_query_params(**kwargs)
        
        response = self.client.get(endpoint, params=params)
        
        customers = []
        for item in response:
            customers.append(Customer.from_dict(item))
        
        return customers
    
    def get(self, customer_id: int) -> Customer:
        response = self.client.get(f'customers/{customer_id}.json')
        return Customer.from_dict(response)
    
    def create(self, name: str, note: Optional[str] = None, hourly_rate: Optional[float] = None) -> Customer:
        data = {
            'customer': {
                'name': name
            }
        }
        
        if note:
            data['customer']['note'] = note
        if hourly_rate:
            data['customer']['hourly-rate'] = hourly_rate
        
        response = self.client.post('customers.json', data)
        return Customer.from_dict(response)
    
    def update(self, customer_id: int, **kwargs) -> Customer:
        data = {'customer': {}}
        
        field_mapping = {
            'name': 'name',
            'note': 'note',
            'hourly_rate': 'hourly-rate',
            'archived': 'archived'
        }
        
        for key, value in kwargs.items():
            if key in field_mapping and value is not None:
                api_key = field_mapping[key]
                data['customer'][api_key] = value
        
        response = self.client.patch(f'customers/{customer_id}.json', data)
        return Customer.from_dict(response)
    
    def delete(self, customer_id: int) -> bool:
        return self.client.delete(f'customers/{customer_id}.json')
    
    def get_active(self) -> List[Customer]:
        return self.list(archived=False)
    
    def get_archived(self) -> List[Customer]:
        return self.list(archived=True)
    
    def search_by_name(self, name: str, archived: bool = False) -> List[Customer]:
        return self.list(name=name, archived=archived)
    
    def archive(self, customer_id: int) -> Customer:
        return self.update(customer_id, archived=True)
    
    def unarchive(self, customer_id: int) -> Customer:
        return self.update(customer_id, archived=False)