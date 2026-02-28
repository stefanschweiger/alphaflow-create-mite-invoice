from typing import List, Optional

from ..models import User
from ..utils import build_query_params


class UsersEndpoint:
    def __init__(self, client):
        self.client = client
    
    def list(self, archived: bool = False, **kwargs) -> List[User]:
        endpoint = 'users/archived.json' if archived else 'users.json'
        params = build_query_params(**kwargs)
        
        response = self.client.get(endpoint, params=params)
        
        users = []
        for item in response:
            users.append(User.from_dict(item))
        
        return users
    
    def get(self, user_id: int) -> User:
        response = self.client.get(f'users/{user_id}.json')
        return User.from_dict(response)
    
    def get_myself(self) -> User:
        response = self.client.get('myself.json')
        return User.from_dict(response)
    
    def create(self, name: str, email: str, note: Optional[str] = None, 
               language: Optional[str] = None, role: Optional[str] = None) -> User:
        data = {
            'user': {
                'name': name,
                'email': email
            }
        }
        
        if note:
            data['user']['note'] = note
        if language:
            data['user']['language'] = language
        if role:
            data['user']['role'] = role
        
        response = self.client.post('users.json', data)
        return User.from_dict(response)
    
    def update(self, user_id: int, **kwargs) -> User:
        data = {'user': {}}
        
        field_mapping = {
            'name': 'name',
            'email': 'email',
            'note': 'note',
            'language': 'language',
            'role': 'role',
            'archived': 'archived'
        }
        
        for key, value in kwargs.items():
            if key in field_mapping and value is not None:
                api_key = field_mapping[key]
                data['user'][api_key] = value
        
        response = self.client.patch(f'users/{user_id}.json', data)
        return User.from_dict(response)
    
    def delete(self, user_id: int) -> bool:
        return self.client.delete(f'users/{user_id}.json')
    
    def get_active(self) -> List[User]:
        return self.list(archived=False)
    
    def get_archived(self) -> List[User]:
        return self.list(archived=True)
    
    def search_by_name(self, name: str, archived: bool = False) -> List[User]:
        return self.list(name=name, archived=archived)
    
    def search_by_email(self, email: str, archived: bool = False) -> List[User]:
        return self.list(email=email, archived=archived)
    
    def archive(self, user_id: int) -> User:
        return self.update(user_id, archived=True)
    
    def unarchive(self, user_id: int) -> User:
        return self.update(user_id, archived=False)