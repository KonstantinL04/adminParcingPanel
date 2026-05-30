from django.db import transaction
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .integrations import archive_event, get_event, get_user, patch_event, patch_user, patch_user_profile
from .models import ModerationCase, ModerationReport, ModerationDecision, UserSanction, EventEditProposal
from .serializers import (
    ModerationCaseSerializer,
    ModerationReportSerializer,
    ModerationDecisionSerializer,
    UserSanctionSerializer,
    ModerationReportCreateSerializer,
    EventEditProposalCreateSerializer,
    ModerationAssignSerializer,
    ModerationResolveSerializer,
)
from .permissions import IsModeratorOrAdmin


class ModerationCaseViewSet(viewsets.ModelViewSet):
    queryset = (
        ModerationCase.objects
        .prefetch_related("reports", "decisions")
        .all()
        .order_by("-created_at")
    )
    serializer_class = ModerationCaseSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        if not self._is_moderator(self.request):
            user_id = str(getattr(self.request.user, "id", "") or "")
            qs = qs.filter(opened_by_user_id=user_id)
        status_value = (self.request.query_params.get("status") or "").strip()
        target_type = (self.request.query_params.get("target_type") or "").strip()
        priority = (self.request.query_params.get("priority") or "").strip()
        assigned = (self.request.query_params.get("assigned_moderator_id") or "").strip()
        if status_value:
            qs = qs.filter(status=status_value)
        if target_type:
            qs = qs.filter(target_type=target_type)
        if priority:
            qs = qs.filter(priority=priority)
        if assigned:
            qs = qs.filter(assigned_moderator_id=assigned)
        return qs

    def _is_moderator(self, request):
        checker = IsModeratorOrAdmin()
        return checker.has_permission(request, self)

    def create(self, request, *args, **kwargs):
        if not self._is_moderator(request):
            return Response({"detail": "Use /report endpoint"}, status=403)
        return super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        if not self._is_moderator(request):
            return Response({"detail": "Moderator role required"}, status=403)
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        if not self._is_moderator(request):
            return Response({"detail": "Moderator role required"}, status=403)
        return super().partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        if not self._is_moderator(request):
            return Response({"detail": "Moderator role required"}, status=403)
        return super().destroy(request, *args, **kwargs)

    @action(detail=False, methods=["post"], url_path="report")
    def report(self, request):
        if not request.user.is_authenticated:
            return Response({"detail": "Authentication required"}, status=401)
        serializer = ModerationReportCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data

        with transaction.atomic():
            case = ModerationCase.objects.create(
                target_type=payload["target_type"],
                target_id=payload["target_id"],
                title=payload.get("title", ""),
                status=ModerationCase.STATUS_OPEN,
                priority=payload.get("priority") or ModerationCase.PRIORITY_MEDIUM,
                reason=payload.get("text", ""),
                opened_by_user_id=payload["reporter_user_id"],
            )
            report = ModerationReport.objects.create(
                case=case,
                reporter_user_id=payload["reporter_user_id"],
                text=payload.get("text", ""),
            )

        data = {
            "case": ModerationCaseSerializer(case, context={"request": request}).data,
            "report": ModerationReportSerializer(report, context={"request": request}).data,
        }
        return Response(data, status=201)

    @action(detail=False, methods=["post"], url_path="propose-event-edit")
    def propose_event_edit(self, request):
        if not request.user.is_authenticated:
            return Response({"detail": "Authentication required"}, status=401)
        serializer = EventEditProposalCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data

        event = get_event(payload["event_id"])
        if not event:
            return Response({"detail": "Event not found"}, status=404)

        with transaction.atomic():
            case = ModerationCase.objects.create(
                target_type=ModerationCase.TARGET_EVENT_EDIT,
                target_id=event["id"],
                title=f"Предложение правки события #{event['id']}",
                status=ModerationCase.STATUS_OPEN,
                priority=payload.get("priority") or ModerationCase.PRIORITY_MEDIUM,
                reason=payload.get("comment", ""),
                opened_by_user_id=payload["proposer_user_id"],
            )
            proposal = EventEditProposal.objects.create(
                case=case,
                event_id=event["id"],
                proposer_user_id=payload["proposer_user_id"],
                proposed_changes=payload["proposed_changes"],
                comment=payload.get("comment", ""),
            )
            ModerationReport.objects.create(
                case=case,
                reporter_user_id=payload["proposer_user_id"],
                text=payload.get("comment", ""),
            )

        return Response(ModerationCaseSerializer(case, context={"request": request}).data, status=201)

    @action(detail=True, methods=["post"], url_path="assign")
    def assign(self, request, pk=None):
        if not self._is_moderator(request):
            return Response({"detail": "Moderator role required"}, status=403)
        case = self.get_object()
        serializer = ModerationAssignSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        case.assigned_moderator_id = serializer.validated_data["moderator_user_id"]
        if case.status == ModerationCase.STATUS_OPEN:
            case.status = ModerationCase.STATUS_IN_REVIEW
        case.save(update_fields=["assigned_moderator_id", "status", "updated_at"])
        return Response(ModerationCaseSerializer(case, context={"request": request}).data)

    @action(detail=True, methods=["post"], url_path="resolve")
    def resolve(self, request, pk=None):
        if not self._is_moderator(request):
            return Response({"detail": "Moderator role required"}, status=403)
        case = self.get_object()
        serializer = ModerationResolveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data

        with transaction.atomic():
            decision = ModerationDecision.objects.create(
                case=case,
                decision=payload["decision"],
                moderator_user_id=payload["moderator_user_id"],
                reason=payload.get("reason", ""),
                meta=payload.get("meta", {}),
            )
            self._apply_decision(case, decision)
            case.status = (
                ModerationCase.STATUS_RESOLVED
                if decision.decision != ModerationDecision.DECISION_REJECT
                else ModerationCase.STATUS_REJECTED
            )
            case.resolved_at = timezone.now()
            case.save(update_fields=["status", "resolved_at", "updated_at"])

        return Response({
            "case": ModerationCaseSerializer(case, context={"request": request}).data,
            "decision": ModerationDecisionSerializer(decision, context={"request": request}).data,
        })

    def _apply_decision(self, case: ModerationCase, decision: ModerationDecision):
        if case.target_type == ModerationCase.TARGET_EVENT_EDIT:
            proposal = getattr(case, "event_edit_proposal", None)
            if not proposal:
                return
            event = get_event(proposal.event_id)
            if not event:
                return
            if decision.decision == ModerationDecision.DECISION_CONFIRM:
                self._apply_event_edit(proposal.event_id, proposal.proposed_changes)
                proposal.status = EventEditProposal.STATUS_APPLIED
                proposal.applied_at = timezone.now()
                proposal.save(update_fields=["status", "applied_at"])
            elif decision.decision == ModerationDecision.DECISION_REJECT:
                proposal.status = EventEditProposal.STATUS_REJECTED
                proposal.save(update_fields=["status"])
            return

        if case.target_type == ModerationCase.TARGET_EVENT:
            event = get_event(case.target_id)
            if not event:
                return
            if decision.decision == ModerationDecision.DECISION_HIDE:
                archive_event(case.target_id)
            elif decision.decision == ModerationDecision.DECISION_RESTORE:
                patch_event(case.target_id, {"is_active": True})
            elif decision.decision == ModerationDecision.DECISION_CONFIRM:
                patch_event(case.target_id, {"status": "confirmed"})
            elif decision.decision == ModerationDecision.DECISION_REJECT:
                patch_event(case.target_id, {"status": "denied"})
            return

        if case.target_type == ModerationCase.TARGET_USER:
            user = get_user(case.target_id)
            if not user:
                return

            if decision.decision == ModerationDecision.DECISION_WARN:
                UserSanction.objects.create(
                    user_id=case.target_id,
                    case=case,
                    sanction_type=UserSanction.TYPE_WARN,
                    reason=decision.reason or "",
                    created_by_user_id=decision.moderator_user_id,
                )
            elif decision.decision == ModerationDecision.DECISION_RESTRICT:
                UserSanction.objects.create(
                    user_id=case.target_id,
                    case=case,
                    sanction_type=UserSanction.TYPE_RESTRICT,
                    reason=decision.reason or "",
                    created_by_user_id=decision.moderator_user_id,
                )
                patch_user_profile(case.target_id, {"status": "restricted"})
            elif decision.decision == ModerationDecision.DECISION_BAN:
                UserSanction.objects.create(
                    user_id=case.target_id,
                    case=case,
                    sanction_type=UserSanction.TYPE_BAN,
                    reason=decision.reason or "",
                    created_by_user_id=decision.moderator_user_id,
                )
                patch_user(case.target_id, {"is_active": False})
                patch_user_profile(case.target_id, {"status": "banned"})

    def _apply_event_edit(self, event_id, changes: dict):
        allowed_fields = {
            "class_item",
            "details",
            "speed_limit",
            "dir_type",
            "direction",
            "distance",
            "angle",
        }
        update_fields = []
        for field, value in (changes or {}).items():
            if field == "location" and isinstance(value, dict):
                coords = value.get("coordinates")
                if isinstance(coords, (list, tuple)) and len(coords) >= 2:
                    update_fields.append(("location", value))
                continue
            if field not in allowed_fields:
                continue
            model_field = "class_item" if field == "class_item" else field
            update_fields.append((model_field, value))
        if update_fields:
            patch_event(event_id, dict(update_fields))


class ModerationDecisionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ModerationDecision.objects.select_related("case").all().order_by("-created_at")
    serializer_class = ModerationDecisionSerializer
    permission_classes = [IsModeratorOrAdmin]


class ModerationReportViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ModerationReport.objects.select_related("case").all().order_by("-created_at")
    serializer_class = ModerationReportSerializer
    permission_classes = [IsModeratorOrAdmin]


class UserSanctionViewSet(viewsets.ModelViewSet):
    queryset = UserSanction.objects.select_related("case").all().order_by("-created_at")
    serializer_class = UserSanctionSerializer
    permission_classes = [IsModeratorOrAdmin]

    def get_queryset(self):
        qs = super().get_queryset()
        user_id = (self.request.query_params.get("user_id") or "").strip()
        status_value = (self.request.query_params.get("status") or "").strip()
        if user_id.isdigit():
            qs = qs.filter(user_id=int(user_id))
        if status_value:
            qs = qs.filter(status=status_value)
        return qs

    def perform_create(self, serializer):
        serializer.save(created_by_user_id=str(self.request.user.id))
