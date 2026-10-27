from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.expense import Expense, Settlement
from app.models.trip import Trip, TripMember
from app.models.user import User
from app.schemas.expense import BalanceResponse, LedgerResponse, TransferSuggestion
from app.schemas.trip import CURRENCIES


def build_ledger(trip: Trip, db: Session) -> LedgerResponse:
    expenses = db.scalars(select(Expense).options(selectinload(Expense.shares))
                         .where(Expense.trip_id == trip.id).order_by(Expense.expense_date.desc(), Expense.id.desc())).all()
    settlements = db.scalars(select(Settlement).where(Settlement.trip_id == trip.id)
                            .order_by(Settlement.settled_on.desc(), Settlement.id.desc())).all()
    current = dict(db.execute(select(User.id, User.username).join(TripMember, TripMember.user_id == User.id)
                              .where(TripMember.trip_id == trip.id)).all())
    people: dict[int, BalanceResponse] = {}

    def person(user_id, name):
        if user_id not in people:
            people[user_id] = BalanceResponse(user_id=user_id, username=current.get(user_id, name), active=user_id in current)
        return people[user_id]

    for user_id, name in current.items():
        person(user_id, name)
    for expense in expenses:
        payer = person(expense.payer_id, expense.payer_name)
        payer.paid_minor += expense.amount_minor
        payer.balance_minor += expense.amount_minor
        for share in expense.shares:
            member = person(share.user_id, share.username)
            member.owed_minor += share.amount_minor
            member.balance_minor -= share.amount_minor
    for settlement in settlements:
        person(settlement.sender_id, settlement.sender_name).balance_minor += settlement.amount_minor
        person(settlement.recipient_id, settlement.recipient_name).balance_minor -= settlement.amount_minor

    debtors = [[member.user_id, -member.balance_minor] for member in sorted(people.values(), key=lambda p: p.user_id)
               if member.balance_minor < 0]
    creditors = [[member.user_id, member.balance_minor] for member in sorted(people.values(), key=lambda p: p.user_id)
                 if member.balance_minor > 0]
    suggestions = []
    left = right = 0
    while left < len(debtors) and right < len(creditors):
        amount = min(debtors[left][1], creditors[right][1])
        suggestions.append(TransferSuggestion(sender_id=debtors[left][0], recipient_id=creditors[right][0], amount_minor=amount))
        debtors[left][1] -= amount
        creditors[right][1] -= amount
        if debtors[left][1] == 0:
            left += 1
        if creditors[right][1] == 0:
            right += 1
    return LedgerResponse(currency=trip.currency, minor_digits=CURRENCIES[trip.currency],
                          total_minor=sum(expense.amount_minor for expense in expenses), expenses=expenses,
                          settlements=settlements, balances=sorted(people.values(), key=lambda p: p.user_id),
                          suggestions=suggestions)
