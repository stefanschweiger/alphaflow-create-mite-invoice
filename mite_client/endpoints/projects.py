from typing import List, Dict, Any, Optional

from ..models import Project
from ..utils import build_query_params


class ProjectsEndpoint:
    def __init__(self, client):
        self.client = client
    
    def list(self, archived: bool = False, **kwargs) -> List[Project]:
        endpoint = 'projects/archived.json' if archived else 'projects.json'
        params = build_query_params(**kwargs)
        
        response = self.client.get(endpoint, params=params)
        
        projects = []
        for item in response:
            projects.append(Project.from_dict(item))
        
        return projects
    
    def get(self, project_id: int) -> Project:
        response = self.client.get(f'projects/{project_id}.json')
        return Project.from_dict(response)
    
    def create(self, name: str, customer_id: Optional[int] = None, note: Optional[str] = None,
               budget: Optional[float] = None, budget_type: Optional[str] = None,
               hourly_rate: Optional[float] = None) -> Project:
        data = {
            'project': {
                'name': name
            }
        }
        
        if customer_id:
            data['project']['customer-id'] = customer_id
        if note:
            data['project']['note'] = note
        if budget:
            data['project']['budget'] = budget
        if budget_type:
            data['project']['budget-type'] = budget_type
        if hourly_rate:
            data['project']['hourly-rate'] = hourly_rate
        
        response = self.client.post('projects.json', data)
        return Project.from_dict(response)
    
    def update(self, project_id: int, **kwargs) -> Project:
        data = {'project': {}}
        
        field_mapping = {
            'name': 'name',
            'note': 'note',
            'customer_id': 'customer-id',
            'budget': 'budget',
            'budget_type': 'budget-type',
            'hourly_rate': 'hourly-rate',
            'archived': 'archived'
        }
        
        for key, value in kwargs.items():
            if key in field_mapping and value is not None:
                api_key = field_mapping[key]
                data['project'][api_key] = value
        
        response = self.client.patch(f'projects/{project_id}.json', data)
        return Project.from_dict(response)
    
    def delete(self, project_id: int) -> bool:
        return self.client.delete(f'projects/{project_id}.json')
    
    def get_by_customer(self, customer_id: int, archived: bool = False) -> List[Project]:
        return self.list(customer_id=customer_id, archived=archived)
    
    def search_by_name(self, name: str, archived: bool = False) -> List[Project]:
        return self.list(name=name, archived=archived)
    
    def get_active(self) -> List[Project]:
        return self.list(archived=False)
    
    def get_archived(self) -> List[Project]:
        return self.list(archived=True)
    
    def archive(self, project_id: int) -> Project:
        return self.update(project_id, archived=True)
    
    def unarchive(self, project_id: int) -> Project:
        return self.update(project_id, archived=False)