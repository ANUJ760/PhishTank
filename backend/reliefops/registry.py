"""In-memory and persistent registry for ReliefOps disaster operations entities."""
from __future__ import annotations

import copy
import threading
import time
from typing import Any

from backend.reliefops.models import (
    AllocationPlan,
    DisasterIncident,
    InventoryItem,
    ReliefCamp,
    ReliefRequest,
    ResourceCategory,
    ResourceType,
    UrgencyLevel,
    Vehicle,
    Warehouse,
)


class ReliefOpsRegistry:
    """Thread-safe state store for disaster incidents, camps, inventories, requests, and plans."""

    def __init__(self):
        self._lock = threading.RLock()
        self.incident: DisasterIncident | None = None
        self.camps: dict[str, ReliefCamp] = {}
        self.resources: dict[str, ResourceType] = {}
        self.warehouses: dict[str, Warehouse] = {}
        self.inventory: dict[str, InventoryItem] = {}
        self.vehicles: dict[str, Vehicle] = {}
        self.requests: dict[str, ReliefRequest] = {}
        self.plans: dict[str, AllocationPlan] = {}
        self.latest_plan_id: str | None = None

        # Seed with initial benchmark scenario
        self.seed_cyclone_disaster_demo()

    def seed_cyclone_disaster_demo(self) -> None:
        """Seed realistic coastal cyclone disaster response scenario."""
        with self._lock:
            self.camps.clear()
            self.resources.clear()
            self.warehouses.clear()
            self.inventory.clear()
            self.vehicles.clear()
            self.requests.clear()
            self.plans.clear()
            self.latest_plan_id = None

            # Incident
            self.incident = DisasterIncident(
                id="INC-2026-CYCLONE",
                name="Cyclone Sagarraj Coastal Impact",
                type="cyclone",
                location="Southern Coastal Bay District",
                severity="critical",
                created_at=time.time(),
            )

            # Resources
            res_items = [
                ResourceType(
                    id="WATER_LITERS",
                    name="Potable Drinking Water",
                    unit="liters",
                    category=ResourceCategory.SURVIVAL,
                    unit_weight_kg=1.0,
                    unit_volume_m3=0.001,
                    priority_weight=10,
                ),
                ResourceType(
                    id="FOOD_RATIONS",
                    name="Ready-to-Eat Emergency Food Packs",
                    unit="packets",
                    category=ResourceCategory.FOOD,
                    unit_weight_kg=0.8,
                    unit_volume_m3=0.002,
                    priority_weight=9,
                ),
                ResourceType(
                    id="MEDICAL_KITS",
                    name="Trauma & First Aid Medical Kits",
                    unit="kits",
                    category=ResourceCategory.MEDICAL,
                    unit_weight_kg=2.5,
                    unit_volume_m3=0.010,
                    priority_weight=10,
                ),
                ResourceType(
                    id="BLANKETS",
                    name="Thermal Emergency Blankets",
                    unit="pieces",
                    category=ResourceCategory.SHELTER,
                    unit_weight_kg=1.2,
                    unit_volume_m3=0.008,
                    priority_weight=6,
                ),
                ResourceType(
                    id="TENTS",
                    name="All-Weather Family Tents",
                    unit="tents",
                    category=ResourceCategory.SHELTER,
                    unit_weight_kg=14.0,
                    unit_volume_m3=0.050,
                    priority_weight=7,
                ),
            ]
            for r in res_items:
                self.resources[r.id] = r

            # Relief Camps
            camp_items = [
                ReliefCamp(
                    id="CAMP-ALPHA",
                    incident_id="INC-2026-CYCLONE",
                    name="Camp Alpha (Central High School)",
                    location="Coastal Sector 1",
                    population=3500,
                    vulnerable_population=850,
                    storage_capacity_m3=120.0,
                    max_weight_capacity_kg=25000.0,
                    access_status="open",
                    contact_person="Dr. K. Sharma",
                ),
                ReliefCamp(
                    id="CAMP-BETA",
                    incident_id="INC-2026-CYCLONE",
                    name="Camp Beta (Delta Island Shelter)",
                    location="Estuary Delta",
                    population=1200,
                    vulnerable_population=480,
                    storage_capacity_m3=50.0,
                    max_weight_capacity_kg=8000.0,
                    access_status="boat_only",  # Bridge washed away
                    contact_person="Capt. R. Deshmukh",
                ),
                ReliefCamp(
                    id="CAMP-GAMMA",
                    incident_id="INC-2026-CYCLONE",
                    name="Camp Gamma (Hilltop Monastery)",
                    location="Ridge Zone B",
                    population=750,
                    vulnerable_population=280,
                    storage_capacity_m3=35.0,
                    max_weight_capacity_kg=5000.0,
                    access_status="air_only",  # Landslides cut roads
                    contact_person="Sister Theresa",
                ),
                ReliefCamp(
                    id="CAMP-DELTA",
                    incident_id="INC-2026-CYCLONE",
                    name="Camp Delta (Highway Community Hall)",
                    location="Inland Highway 4",
                    population=2200,
                    vulnerable_population=410,
                    storage_capacity_m3=90.0,
                    max_weight_capacity_kg=18000.0,
                    access_status="restricted_road",  # Debris partially cleared
                    contact_person="M. Patel",
                ),
            ]
            for c in camp_items:
                self.camps[c.id] = c

            # Warehouses
            wh_items = [
                Warehouse(
                    id="WH-CENTRAL",
                    name="Central Logistics Staging Base",
                    location="Air Base Depot",
                    is_operational=True,
                    total_capacity_m3=600.0,
                ),
                Warehouse(
                    id="WH-PORT",
                    name="Harbor Forward Relief Depot",
                    location="Coastal Pier 3",
                    is_operational=True,
                    total_capacity_m3=350.0,
                ),
            ]
            for w in wh_items:
                self.warehouses[w.id] = w

            # Inventory (Stocked supplies: intentional scarcity to exercise solver!)
            # Total requested water will be ~15,500L; available will be 10,000L.
            inv_items = [
                # WH-CENTRAL
                InventoryItem(
                    id="INV-C-WATER",
                    warehouse_id="WH-CENTRAL",
                    resource_id="WATER_LITERS",
                    quantity_available=7000,
                ),
                InventoryItem(
                    id="INV-C-FOOD",
                    warehouse_id="WH-CENTRAL",
                    resource_id="FOOD_RATIONS",
                    quantity_available=5000,
                ),
                InventoryItem(
                    id="INV-C-MED",
                    warehouse_id="WH-CENTRAL",
                    resource_id="MEDICAL_KITS",
                    quantity_available=300,
                ),
                InventoryItem(
                    id="INV-C-BLANKETS",
                    warehouse_id="WH-CENTRAL",
                    resource_id="BLANKETS",
                    quantity_available=2000,
                ),
                InventoryItem(
                    id="INV-C-TENTS",
                    warehouse_id="WH-CENTRAL",
                    resource_id="TENTS",
                    quantity_available=150,
                ),
                # WH-PORT
                InventoryItem(
                    id="INV-P-WATER",
                    warehouse_id="WH-PORT",
                    resource_id="WATER_LITERS",
                    quantity_available=3000,
                ),
                InventoryItem(
                    id="INV-P-FOOD",
                    warehouse_id="WH-PORT",
                    resource_id="FOOD_RATIONS",
                    quantity_available=2500,
                ),
                InventoryItem(
                    id="INV-P-MED",
                    warehouse_id="WH-PORT",
                    resource_id="MEDICAL_KITS",
                    quantity_available=120,
                ),
                InventoryItem(
                    id="INV-P-BLANKETS",
                    warehouse_id="WH-PORT",
                    resource_id="BLANKETS",
                    quantity_available=800,
                ),
                InventoryItem(
                    id="INV-P-TENTS",
                    warehouse_id="WH-PORT",
                    resource_id="TENTS",
                    quantity_available=60,
                ),
            ]
            for inv in inv_items:
                self.inventory[inv.id] = inv

            # Vehicles Fleet
            veh_items = [
                Vehicle(
                    id="VEH-TRUCK-1",
                    name="Heavy Logistics Truck Alpha",
                    vehicle_type="heavy_truck",
                    max_weight_kg=12000.0,
                    max_volume_m3=40.0,
                    is_available=True,
                    supported_access=["open"],
                ),
                Vehicle(
                    id="VEH-TRUCK-2",
                    name="4x4 High-Clearance Truck Bravo",
                    vehicle_type="light_truck",
                    max_weight_kg=4500.0,
                    max_volume_m3=18.0,
                    is_available=True,
                    supported_access=["open", "restricted_road"],
                ),
                Vehicle(
                    id="VEH-BOAT-1",
                    name="Disaster Response Rescue Boat 01",
                    vehicle_type="boat",
                    max_weight_kg=4000.0,
                    max_volume_m3=15.0,
                    is_available=True,
                    supported_access=["boat_only", "open"],
                ),
                Vehicle(
                    id="VEH-HELI-1",
                    name="Relief Aviation Helicopter Charlie",
                    vehicle_type="helicopter",
                    max_weight_kg=2200.0,
                    max_volume_m3=9.0,
                    is_available=True,
                    supported_access=["air_only", "restricted_road", "open"],
                ),
            ]
            for v in veh_items:
                self.vehicles[v.id] = v

            # Camp Relief Requests
            raw_requests = [
                # CAMP-ALPHA (Largest camp, open road)
                ("CAMP-ALPHA", "WATER_LITERS", 7000, UrgencyLevel.CRITICAL, "Drinking wells submerged"),
                ("CAMP-ALPHA", "FOOD_RATIONS", 4500, UrgencyLevel.HIGH, "3-day buffer requested"),
                ("CAMP-ALPHA", "MEDICAL_KITS", 250, UrgencyLevel.CRITICAL, "Trauma and cholera prevention"),
                ("CAMP-ALPHA", "BLANKETS", 1500, UrgencyLevel.MEDIUM, "Rain-drenched shelter bedding"),
                ("CAMP-ALPHA", "TENTS", 80, UrgencyLevel.MEDIUM, "Overflow shelter tents"),
                # CAMP-BETA (Island, boat_only, high vulnerable %)
                ("CAMP-BETA", "WATER_LITERS", 3000, UrgencyLevel.CRITICAL, "Island water supply salinity contaminated"),
                ("CAMP-BETA", "FOOD_RATIONS", 1800, UrgencyLevel.CRITICAL, "Zero local provisions remain"),
                ("CAMP-BETA", "MEDICAL_KITS", 100, UrgencyLevel.HIGH, "Infant pediatric medicine urgently required"),
                ("CAMP-BETA", "BLANKETS", 600, UrgencyLevel.HIGH, "Children sleeping without covers"),
                ("CAMP-BETA", "TENTS", 40, UrgencyLevel.MEDIUM, "Classrooms fully occupied"),
                # CAMP-GAMMA (Hilltop, air_only, isolated)
                ("CAMP-GAMMA", "WATER_LITERS", 1500, UrgencyLevel.CRITICAL, "Mountain stream silt blocked"),
                ("CAMP-GAMMA", "FOOD_RATIONS", 1000, UrgencyLevel.HIGH, "Isolated community food reserves empty"),
                ("CAMP-GAMMA", "MEDICAL_KITS", 60, UrgencyLevel.CRITICAL, "Elderly respiratory medications required"),
                ("CAMP-GAMMA", "BLANKETS", 400, UrgencyLevel.MEDIUM, "Cold mountain winds"),
                # CAMP-DELTA (Highway community hall, restricted road)
                ("CAMP-DELTA", "WATER_LITERS", 4000, UrgencyLevel.HIGH, "Piped water offline"),
                ("CAMP-DELTA", "FOOD_RATIONS", 2500, UrgencyLevel.HIGH, "Canteen kitchen destroyed"),
                ("CAMP-DELTA", "MEDICAL_KITS", 90, UrgencyLevel.MEDIUM, "First aid kit replenishment"),
                ("CAMP-DELTA", "BLANKETS", 800, UrgencyLevel.LOW, "Secondary supply"),
                ("CAMP-DELTA", "TENTS", 50, UrgencyLevel.MEDIUM, "Family temporary shelters"),
            ]

            for i, (c_id, r_id, qty, urg, note) in enumerate(raw_requests, start=1):
                req_id = f"REQ-SEED-{i:03d}"
                self.requests[req_id] = ReliefRequest(
                    id=req_id,
                    camp_id=c_id,
                    resource_id=r_id,
                    quantity_requested=qty,
                    urgency=urg,
                    evidence_notes=note,
                    status="pending",
                    created_at=time.time(),
                )

    def get_camps(self) -> list[ReliefCamp]:
        with self._lock:
            return list(self.camps.values())

    def get_camp(self, camp_id: str) -> ReliefCamp | None:
        with self._lock:
            return self.camps.get(camp_id)

    def get_resources(self) -> list[ResourceType]:
        with self._lock:
            return list(self.resources.values())

    def get_warehouses(self) -> list[Warehouse]:
        with self._lock:
            return list(self.warehouses.values())

    def get_inventory(self) -> list[InventoryItem]:
        with self._lock:
            return list(self.inventory.values())

    def get_vehicles(self) -> list[Vehicle]:
        with self._lock:
            return list(self.vehicles.values())

    def get_requests(self) -> list[ReliefRequest]:
        with self._lock:
            return list(self.requests.values())

    def save_request(self, request: ReliefRequest) -> ReliefRequest:
        with self._lock:
            self.requests[request.id] = request
            return request

    def save_plan(self, plan: AllocationPlan) -> None:
        with self._lock:
            self.plans[plan.plan_id] = plan
            self.latest_plan_id = plan.plan_id

    def get_latest_plan(self) -> AllocationPlan | None:
        with self._lock:
            if not self.latest_plan_id:
                return None
            return self.plans.get(self.latest_plan_id)

    def get_plan(self, plan_id: str) -> AllocationPlan | None:
        with self._lock:
            return self.plans.get(plan_id)

    def update_warehouse_status(self, warehouse_id: str, is_operational: bool) -> Warehouse | None:
        with self._lock:
            wh = self.warehouses.get(warehouse_id)
            if wh:
                wh.is_operational = is_operational
            return wh

    def update_camp_access(self, camp_id: str, access_status: str) -> ReliefCamp | None:
        with self._lock:
            camp = self.camps.get(camp_id)
            if camp:
                camp.access_status = access_status
            return camp

    def add_inventory(self, warehouse_id: str, resource_id: str, quantity: int) -> InventoryItem:
        with self._lock:
            existing = next(
                (
                    item
                    for item in self.inventory.values()
                    if item.warehouse_id == warehouse_id and item.resource_id == resource_id
                ),
                None,
            )
            if existing:
                existing.quantity_available += quantity
                return existing
            new_item = InventoryItem(
                id=f"INV-ADD-{int(time.time())}",
                warehouse_id=warehouse_id,
                resource_id=resource_id,
                quantity_available=quantity,
            )
            self.inventory[new_item.id] = new_item
            return new_item


# Global registry singleton
_registry: ReliefOpsRegistry | None = None


def get_reliefops_registry() -> ReliefOpsRegistry:
    global _registry
    if _registry is None:
        _registry = ReliefOpsRegistry()
    return _registry
