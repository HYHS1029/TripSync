from fastapi import APIRouter, HTTPException, Response
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.api.trips import CurrentUser, Database, TripId, get_member_trip
from app.database import commit_transaction
from app.models.activity import Activity
from app.models.expense import Expense, ExpenseShare, Settlement
from app.models.trip import TripMember
from app.models.user import User
from app.schemas.expense import ExpenseInput, ExpenseResponse, LedgerResponse, SettlementInput, SettlementResponse
from app.services.ledger import build_ledger


router = APIRouter(prefix="/trips/{trip_id}", tags=["expenses"])
MAX_ENTRIES = 1000


def find_expense(trip_id, expense_id, db):
    expense = db.scalar(select(Expense).options(selectinload(Expense.shares)).where(
        Expense.trip_id == trip_id, Expense.id == expense_id))
    if expense is None:
        raise HTTPException(status_code=404, detail="Expense not found")
    return expense


def can_edit(trip, entry, user):
    if user.id not in (trip.owner_id, entry.created_by):
        raise HTTPException(status_code=403, detail="Only creator or owner can edit this entry")


def apply_expense(payload, expense, trip, db, *, existing=False):
    names = dict(db.execute(select(User.id, User.username).join(TripMember, TripMember.user_id == User.id)
                            .where(TripMember.trip_id == trip.id)).all())
    # Historical parties remain editable after leaving, but cannot be added to new expenses.
    if existing:
        names.setdefault(expense.payer_id, expense.payer_name)
        for share in expense.shares:
            names.setdefault(share.user_id, share.username)
    if not {payload.payer_id, *payload.participant_ids} <= names.keys():
        raise HTTPException(status_code=422, detail="Parties must belong to this trip")
    if payload.activity_id is not None and db.scalar(select(Activity.id).where(
        Activity.id == payload.activity_id, Activity.trip_id == trip.id)) is None:
        raise HTTPException(status_code=422, detail="Activity must belong to this trip")
    if existing:
        expense.shares.clear()
        db.flush()
    for field in ("title", "expense_date", "category", "amount_minor", "payer_id", "split_mode", "activity_id", "notes"):
        setattr(expense, field, getattr(payload, field))
    expense.currency = trip.currency
    expense.payer_name = names[payload.payer_id]
    ids = sorted(payload.participant_ids)
    quotient, remainder = divmod(payload.amount_minor, len(ids))
    amounts = ({user_id: quotient + (index < remainder) for index, user_id in enumerate(ids)}
               if payload.split_mode == "equal" else {share.user_id: share.amount_minor for share in payload.custom_shares})
    expense.shares = [ExpenseShare(user_id=user_id, username=names[user_id], amount_minor=amounts[user_id]) for user_id in ids]


@router.get("/ledger", response_model=LedgerResponse)
def read_ledger(trip_id: TripId, db: Database, user: CurrentUser):
    return build_ledger(get_member_trip(trip_id, user.id, db), db)


@router.post("/expenses", response_model=ExpenseResponse, status_code=201)
def create_expense(trip_id: TripId, payload: ExpenseInput, db: Database, user: CurrentUser):
    trip = get_member_trip(trip_id, user.id, db, lock=True)
    if db.scalar(select(func.count()).select_from(Expense).where(Expense.trip_id == trip_id)) >= MAX_ENTRIES:
        raise HTTPException(status_code=409, detail="Expense limit reached")
    expense = Expense(trip_id=trip.id, created_by=user.id)
    apply_expense(payload, expense, trip, db)
    db.add(expense)
    commit_transaction(db)
    return expense


@router.put("/expenses/{expense_id}", response_model=ExpenseResponse)
def update_expense(trip_id: TripId, expense_id: TripId, payload: ExpenseInput, db: Database, user: CurrentUser):
    trip = get_member_trip(trip_id, user.id, db, lock=True)
    expense = find_expense(trip_id, expense_id, db)
    can_edit(trip, expense, user)
    apply_expense(payload, expense, trip, db, existing=True)
    commit_transaction(db)
    return expense


@router.delete("/expenses/{expense_id}", status_code=204)
def delete_expense(trip_id: TripId, expense_id: TripId, db: Database, user: CurrentUser):
    trip = get_member_trip(trip_id, user.id, db, lock=True)
    expense = find_expense(trip_id, expense_id, db)
    can_edit(trip, expense, user)
    db.delete(expense)
    commit_transaction(db)
    return Response(status_code=204)


@router.post("/settlements", response_model=SettlementResponse, status_code=201)
def create_settlement(trip_id: TripId, payload: SettlementInput, db: Database, user: CurrentUser):
    trip = get_member_trip(trip_id, user.id, db, lock=True)
    if db.scalar(select(func.count()).select_from(Settlement).where(Settlement.trip_id == trip_id)) >= MAX_ENTRIES:
        raise HTTPException(status_code=409, detail="Settlement limit reached")
    people = {person.user_id: person for person in build_ledger(trip, db).balances}
    sender, recipient = people.get(payload.sender_id), people.get(payload.recipient_id)
    if sender is None or recipient is None or payload.amount_minor > min(-sender.balance_minor, recipient.balance_minor):
        raise HTTPException(status_code=409, detail="Balances changed or repayment exceeds outstanding balance")
    settlement = Settlement(**payload.model_dump(), trip_id=trip.id, currency=trip.currency,
                            sender_name=sender.username, recipient_name=recipient.username, created_by=user.id)
    db.add(settlement)
    commit_transaction(db)
    return settlement


@router.delete("/settlements/{settlement_id}", status_code=204)
def delete_settlement(trip_id: TripId, settlement_id: TripId, db: Database, user: CurrentUser):
    trip = get_member_trip(trip_id, user.id, db, lock=True)
    settlement = db.scalar(select(Settlement).where(Settlement.id == settlement_id, Settlement.trip_id == trip.id))
    if settlement is None:
        raise HTTPException(status_code=404, detail="Settlement not found")
    can_edit(trip, settlement, user)
    db.delete(settlement)
    commit_transaction(db)
    return Response(status_code=204)
