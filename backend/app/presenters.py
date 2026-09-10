"""Stable API representations shared by domain routers and services."""

from app.models import EmergencyContact, Patient, Reminder, User


def public_reminder(reminder: Reminder) -> dict:
    return {
        "id": reminder.id,
        "patientId": reminder.patient_id,
        "type": reminder.type,
        "title": reminder.title,
        "description": reminder.description,
        "scheduledTime": reminder.scheduled_time,
        "repeatRule": reminder.repeat_rule,
        "enabled": reminder.enabled,
        "completed": reminder.completed,
        "status": reminder.status,
        "snoozedUntil": reminder.snoozed_until,
        "acknowledgedAt": reminder.acknowledged_at,
        "timezoneName": reminder.timezone_name,
    }


def public_patient(patient: Patient, user: User) -> dict:
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "age": patient.age,
        "preferredLanguage": patient.preferred_language,
        "nextDifficulty": patient.next_difficulty,
        "personalizationOverride": patient.personalization_override,
    }


def public_contact(contact: EmergencyContact) -> dict:
    return {
        "id": contact.id,
        "patientId": contact.patient_id,
        "name": contact.name,
        "phone": contact.phone,
        "relationship": contact.relationship,
        "priority": contact.priority,
        "active": contact.active,
    }
