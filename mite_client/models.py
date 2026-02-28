from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any


@dataclass
class TimeEntry:
    id: int
    minutes: int
    date_at: str
    note: Optional[str] = None
    billable: bool = True
    locked: bool = False
    revenue: Optional[float] = None
    hourly_rate: Optional[float] = None
    user_id: Optional[int] = None
    user_name: Optional[str] = None
    customer_id: Optional[int] = None
    customer_name: Optional[str] = None
    project_id: Optional[int] = None
    project_name: Optional[str] = None
    service_id: Optional[int] = None
    service_name: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TimeEntry':
        time_entry = data.get('time_entry', data.get('time-entry', data))
        return cls(
            id=time_entry['id'],
            minutes=time_entry['minutes'],
            date_at=time_entry['date_at'],
            note=time_entry.get('note'),
            billable=time_entry.get('billable', True),
            locked=time_entry.get('locked', False),
            revenue=time_entry.get('revenue'),
            hourly_rate=time_entry.get('hourly_rate'),
            user_id=time_entry.get('user_id'),
            user_name=time_entry.get('user_name'),
            customer_id=time_entry.get('customer_id'),
            customer_name=time_entry.get('customer_name'),
            project_id=time_entry.get('project_id'),
            project_name=time_entry.get('project_name'),
            service_id=time_entry.get('service_id'),
            service_name=time_entry.get('service_name'),
            created_at=time_entry.get('created-at'),
            updated_at=time_entry.get('updated-at'),
        )

    @property
    def hours(self) -> float:
        return round(self.minutes / 60.0, 2)


@dataclass
class Project:
    id: int
    name: str
    note: Optional[str] = None
    customer_id: Optional[int] = None
    customer_name: Optional[str] = None
    budget: Optional[float] = None
    budget_type: Optional[str] = None
    hourly_rate: Optional[float] = None
    active_hourly_rate: Optional[float] = None
    archived: bool = False
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Project':
        project = data.get('project', data)
        return cls(
            id=project['id'],
            name=project['name'],
            note=project.get('note'),
            customer_id=project.get('customer-id'),
            customer_name=project.get('customer-name'),
            budget=project.get('budget'),
            budget_type=project.get('budget-type'),
            hourly_rate=project.get('hourly-rate'),
            active_hourly_rate=project.get('active-hourly-rate'),
            archived=project.get('archived', False),
            created_at=project.get('created-at'),
            updated_at=project.get('updated-at'),
        )


@dataclass
class Customer:
    id: int
    name: str
    note: Optional[str] = None
    hourly_rate: Optional[float] = None
    active_hourly_rate: Optional[float] = None
    archived: bool = False
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Customer':
        customer = data.get('customer', data)
        return cls(
            id=customer['id'],
            name=customer['name'],
            note=customer.get('note'),
            hourly_rate=customer.get('hourly-rate'),
            active_hourly_rate=customer.get('active-hourly-rate'),
            archived=customer.get('archived', False),
            created_at=customer.get('created-at'),
            updated_at=customer.get('updated-at'),
        )


@dataclass
class Service:
    id: int
    name: str
    note: Optional[str] = None
    hourly_rate: Optional[float] = None
    active_hourly_rate: Optional[float] = None
    billable: bool = True
    archived: bool = False
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Service':
        service = data.get('service', data)
        return cls(
            id=service['id'],
            name=service['name'],
            note=service.get('note'),
            hourly_rate=service.get('hourly-rate'),
            active_hourly_rate=service.get('active-hourly-rate'),
            billable=service.get('billable', True),
            archived=service.get('archived', False),
            created_at=service.get('created-at'),
            updated_at=service.get('updated-at'),
        )


@dataclass
class User:
    id: int
    name: str
    email: str
    note: Optional[str] = None
    language: Optional[str] = None
    role: Optional[str] = None
    archived: bool = False
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'User':
        user = data.get('user', data)
        return cls(
            id=user['id'],
            name=user['name'],
            email=user['email'],
            note=user.get('note'),
            language=user.get('language'),
            role=user.get('role'),
            archived=user.get('archived', False),
            created_at=user.get('created-at'),
            updated_at=user.get('updated-at'),
        )