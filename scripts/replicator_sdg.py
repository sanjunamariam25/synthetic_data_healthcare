import asyncio
import random
import math

import omni
import omni.timeline

from pxr import UsdGeom, UsdShade, Sdf, Gf


# ============================================================
# CONFIGURATION
# ============================================================

NUM_VARIATIONS = 30
VARIATION_INTERVAL = 2.0
RANDOM_SEED = 42

MATERIAL_ROOT = "/World/RandomizedMaterials"
CAMERA_PATH = "/World/hospital/Camera"

# Change True to False if you want variations only while
# the Omniverse timeline is playing.
RUN_WHILE_PAUSED = True

# Position offsets are in stage units.
# The script progressively increases the search radius
# if it cannot find a sufficiently separated position.
PLACEMENT_RADII = [0.4, 0.8, 1.2, 1.8, 2.5, 3.5]

# Approximate minimum distances between object origins.
MIN_DISTANCE = 0.80
CHAIR_DISTANCE = 0.95
WHEELCHAIR_DISTANCE = 1.25
CART_DISTANCE = 1.10
SMALL_OBJECT_DISTANCE = 0.40

# Limit vertical displacement so objects do not move far
# above or below their original height.
MAX_Z_OFFSET = 0.04

stage = omni.usd.get_context().get_stage()
timeline = omni.timeline.get_timeline_interface()

if stage is None:
    raise RuntimeError("No USD stage is open.")


# ============================================================
# OBJECTS TO RANDOMIZE
# ============================================================

OBJECT_PATHS = [
    "/World/hospital/SM_Book_01c_2",
    "/World/hospital/SM_Book_01d_5",
    "/World/hospital/SM_MedShelf_01d_67",

    "/World/hospital/SM_WheelChair_01a_37",
    "/World/hospital/SM_WheelChair_01a2",

    "/World/hospital/SM_Chair_01a_24",
    "/World/hospital/SM_Chair_01a10",
    "/World/hospital/SM_Chair_01a11",
    "/World/hospital/SM_Chair_01a12",
    "/World/hospital/SM_Chair_01a13",
    "/World/hospital/SM_Chair_01a14",
    "/World/hospital/SM_Chair_01a15",
    "/World/hospital/SM_Chair_01a2_68",
    "/World/hospital/SM_Chair_01a3",
    "/World/hospital/SM_Chair_01a4",
    "/World/hospital/SM_Chair_01a5",
    "/World/hospital/SM_Chair_01a6",
    "/World/hospital/SM_Chair_01a7",
    "/World/hospital/SM_Chair_01a8",
    "/World/hospital/SM_Chair_01a9",
    "/World/hospital/SM_Chair_02a7"

    "/World/hospital/SM_Chair_02a4",
    "/World/hospital/SM_Chair_02a5",

    "/World/hospital/SM_SupplyCart_02a4_114",
    "/World/hospital/SM_Scale_01a2_111",
    "/World/hospital/SM_MedicalBag_01a_105",
    "/World/hospital/SM_SoapDispenser_01a4",
    "/World/hospital/SM_FirstAidKit_01a_138",
    "/World/hospital/SM_SideTable_02a6",
]


# ============================================================
# MATERIAL-ONLY TARGETS
# ============================================================

SURFACE_PATHS = [
    "/World/hospital/Geo_Floor_Costum16_14",
    "/World/hospital/Geo_Floor_Costum14_5",
    "/World/hospital/Geo_Floor_Costum22_95",

    "/World/hospital/Geo_M2_WindowWallLeft_562",
    "/World/hospital/Geo_M2_WindowWallLeft2",
    "/World/hospital/Geo_M2_WindowWallRight_559",
    "/World/hospital/Geo_M2_WindowWallRight2",

    "/World/hospital/SM_ReceptionDesk_01a2_52",
    "/World/hospital/SM_ReceptionDesk_01a_46",
    "/World/hospital/Geo_W_WallBase2",
    "/World/hospital/Geo_W_WallCornerBase2_21"
]

MATERIAL_TARGETS = list(
    dict.fromkeys(OBJECT_PATHS + SURFACE_PATHS)
)


# ============================================================
# PERSISTENT BASELINE CACHE
#
# Keeps original transforms when the script is rerun in the
# same stage. Prevents random offsets accumulating over time.
# ============================================================

BASELINE_KEY = "_hospital_randomizer_baselines_v2"

baseline_cache = globals().get(BASELINE_KEY)

if baseline_cache is None:
    baseline_cache = {}

globals()[BASELINE_KEY] = baseline_cache


# ============================================================
# HELPER: GET LOCAL MATRIX
# ============================================================

def get_local_matrix(xformable):

    result = xformable.GetLocalTransformation()

    if isinstance(result, tuple):
        return result[0]

    return result


# ============================================================
# HELPER: CLASSIFY OBJECT
# ============================================================

def object_category(path):

    name = path.split("/")[-1].lower()

    if "wheelchair" in name:
        return "wheelchair"

    if "supplycart" in name:
        return "cart"

    if "chair" in name:
        return "chair"

    if "book" in name:
        return "book"

    if "medshelf" in name:
        return "furniture"

    if "sidetable" in name:
        return "furniture"

    if "medicalbag" in name or "firstaidkit" in name:
        return "medical"

    if "soapdispenser" in name or "scale" in name:
        return "medical"

    return "general"


# ============================================================
# HELPER: MINIMUM SEPARATION
# ============================================================

def required_distance(path):

    category = object_category(path)

    if category == "wheelchair":
        return WHEELCHAIR_DISTANCE

    if category == "chair":
        return CHAIR_DISTANCE

    if category == "cart":
        return CART_DISTANCE

    if category in ("book", "medical"):
        return SMALL_OBJECT_DISTANCE

    return MIN_DISTANCE


def distance_2d(a, b):

    dx = float(a[0] - b[0])
    dy = float(a[1] - b[1])

    return math.sqrt(dx * dx + dy * dy)


# ============================================================
# CREATE MATERIAL PALETTE
# ============================================================

def create_material_palette():

    existing = stage.GetPrimAtPath(MATERIAL_ROOT)

    if existing.IsValid():
        stage.RemovePrim(MATERIAL_ROOT)

    stage.DefinePrim(MATERIAL_ROOT, "Scope")

    materials = []

    for i in range(NUM_VARIATIONS):

        rng = random.Random(RANDOM_SEED + i * 31)

        material_path = "{}/Material_{:02d}".format(
            MATERIAL_ROOT, i
        )

        shader_path = material_path + "/PreviewSurface"

        material = UsdShade.Material.Define(
            stage, material_path
        )

        shader = UsdShade.Shader.Define(
            stage, shader_path
        )

        shader.CreateIdAttr("UsdPreviewSurface")

        color = Gf.Vec3f(
            rng.uniform(0.12, 0.95),
            rng.uniform(0.12, 0.95),
            rng.uniform(0.12, 0.95)
        )

        shader.CreateInput(
            "diffuseColor",
            Sdf.ValueTypeNames.Color3f
        ).Set(color)

        shader.CreateInput(
            "roughness",
            Sdf.ValueTypeNames.Float
        ).Set(rng.uniform(0.25, 0.95))

        shader.CreateInput(
            "metallic",
            Sdf.ValueTypeNames.Float
        ).Set(rng.uniform(0.0, 0.15))

        shader.CreateOutput(
            "surface",
            Sdf.ValueTypeNames.Token
        )

        material.CreateSurfaceOutput().ConnectToSource(
            shader.ConnectableAPI(),
            "surface"
        )

        materials.append(material)

    print("[Materials] Created {} materials.".format(
        len(materials)
    ))

    return materials


# ============================================================
# APPLY MATERIAL TO MESHES
# ============================================================

def apply_material(asset_path, material):

    root = stage.GetPrimAtPath(asset_path)

    if not root.IsValid():
        print("[Missing material target] {}".format(asset_path))
        return

    meshes = []

    if root.IsA(UsdGeom.Mesh) and not root.IsInstanceProxy():
        meshes.append(root)

    for prim in stage.Traverse():

        if not prim.IsValid():
            continue

        if prim.IsInstanceProxy():
            continue

        if not prim.IsA(UsdGeom.Mesh):
            continue

        path = str(prim.GetPath())
        root_path = str(root.GetPath())

        if path.startswith(root_path + "/"):
            meshes.append(prim)

    unique_meshes = {
        str(mesh.GetPath()): mesh
        for mesh in meshes
    }

    if not unique_meshes:
        print("[No editable meshes] {}".format(asset_path))
        return

    for mesh in unique_meshes.values():

        try:
            binding_api = UsdShade.MaterialBindingAPI.Apply(mesh)
            binding_api.Bind(material)

        except Exception as exc:
            print(
                "[Material warning] {}: {}".format(
                    mesh.GetPath(), exc
                )
            )


# ============================================================
# PREPARE TRANSFORM
#
# Capture the original local transform and use one matrix op.
# This avoids relying on appended translate/rotate ops whose
# ordering can produce unexpected results.
# ============================================================

def prepare_transform(path):

    prim = stage.GetPrimAtPath(path)

    if not prim.IsValid():
        print("[Missing object] {}".format(path))
        return None

    if prim.IsInstanceProxy():
        print("[Instance proxy skipped] {}".format(path))
        return None

    xformable = UsdGeom.Xformable(prim)

    if not xformable:
        print("[Not transformable] {}".format(path))
        return None

    try:

        cached = baseline_cache.get(path)

        if cached is None:

            # Capture the transform currently used by the object.
            original_matrix = get_local_matrix(xformable)

            original_transform = Gf.Transform(original_matrix)

            # Preserve original local position, rotation and scale.
            original_translation = Gf.Vec3d(
                original_transform.GetTranslation()
            )

            original_rotation = Gf.Rotation(
                original_transform.GetRotation()
            )

            original_scale = Gf.Vec3d(
                original_transform.GetScale()
            )

            cached = {
                "original_matrix": original_matrix,
                "translation": original_translation,
                "rotation": original_rotation,
                "scale": original_scale,
            }

            baseline_cache[path] = cached

        # Find the matrix op created by this randomizer.
        matrix_op = None

        for op in xformable.GetOrderedXformOps():

            if op.GetOpName() == "xformOp:transform:randomizerV2":
                matrix_op = op
                break

        if matrix_op is None:

            matrix_op = xformable.AddTransformOp(
                UsdGeom.XformOp.PrecisionDouble,
                "randomizerV2"
            )

        # Put the complete original transform into one op.
        # This avoids composing with stale randomizer offsets.
        matrix_op.Set(cached["original_matrix"])

        # Use only this matrix op for this prim's local transform.
        # The original transform is preserved in the cached matrix.
        xformable.SetXformOpOrder([matrix_op])

        return {
            "path": path,
            "prim": prim,
            "matrix_op": matrix_op,
            "translation": cached["translation"],
            "rotation": cached["rotation"],
            "scale": cached["scale"],
            "original_matrix": cached["original_matrix"],
        }

    except Exception as exc:

        print(
            "[Transform setup error] {}: {}".format(
                path, exc
            )
        )

        return None


# ============================================================
# GENERATE MORE DIVERSE POSITIONS
#
# These objects are direct children of /World/hospital in
# the configured paths, so their local XY positions can be
# compared for approximate separation.
# ============================================================

def generate_positions(objects, variation_index):

    rng = random.Random(
        RANDOM_SEED + variation_index * 7919
    )

    shuffled = list(objects)
    rng.shuffle(shuffled)

    placed = []
    positions = {}

    for data in shuffled:

        path = data["path"]
        base = data["translation"]

        chosen = None

        # Try increasingly larger position ranges.
        for radius in PLACEMENT_RADII:

            for attempt in range(250):

                dx = rng.uniform(-radius, radius)
                dy = rng.uniform(-radius, radius)

                candidate = Gf.Vec3d(
                    base[0] + dx,
                    base[1] + dy,
                    base[2] + rng.uniform(
                        -MAX_Z_OFFSET,
                        MAX_Z_OFFSET
                    )
                )

                is_safe = True

                for other_path, other_position in placed:

                    min_dist = max(
                        required_distance(path),
                        required_distance(other_path)
                    )

                    if distance_2d(
                        candidate,
                        other_position
                    ) < min_dist:

                        is_safe = False
                        break

                if is_safe:
                    chosen = candidate
                    break

            if chosen is not None:
                break

        if chosen is None:

            # Last attempt uses a wider area.
            # If this also overlaps, a warning is printed.
            for attempt in range(500):

                radius = 4.0 + (attempt % 5) * 1.0

                candidate = Gf.Vec3d(
                    base[0] + rng.uniform(-radius, radius),
                    base[1] + rng.uniform(-radius, radius),
                    base[2]
                )

                is_safe = True

                for other_path, other_position in placed:

                    min_dist = max(
                        required_distance(path),
                        required_distance(other_path)
                    )

                    if distance_2d(
                        candidate,
                        other_position
                    ) < min_dist:

                        is_safe = False
                        break

                if is_safe:
                    chosen = candidate
                    break

        if chosen is None:

            # Keep the original position rather than inventing
            # a potentially extreme position.
            chosen = Gf.Vec3d(
                base[0],
                base[1],
                base[2]
            )

            print(
                "[Spacing warning] Could not find a safe position: {}"
                .format(path)
            )

        positions[path] = chosen
        placed.append((path, chosen))

    print(
        "[Placement] Generated positions for {} objects."
        .format(len(positions))
    )

    return positions


# ============================================================
# ROTATION RANGES
#
# Different object types get different rotation limits.
# Chairs and wheelchairs mainly rotate in yaw, with smaller
# X/Y changes to avoid making furniture excessively tilted.
# Small items receive larger 3-axis rotations.
# ============================================================

def get_rotation_ranges(path):

    category = object_category(path)

    if category == "wheelchair":
        return (5.0, 5.0, 180.0)

    if category == "chair":
        return (7.0, 7.0, 180.0)

    if category == "cart":
        return (4.0, 4.0, 150.0)

    if category == "furniture":
        return (3.0, 3.0, 120.0)

    if category == "book":
        return (35.0, 35.0, 180.0)

    if category == "medical":
        return (25.0, 25.0, 180.0)

    return (25.0, 25.0, 180.0)


# ============================================================
# APPLY DIVERSE POSE
#
# Builds a fresh transform from the cached original transform
# for every variation. Translation offsets never accumulate.
# ============================================================

def apply_pose(data, position, variation_index):

    path = data["path"]

    # Unique RNG for each object and variation.
    seed_value = (
        RANDOM_SEED
        + variation_index * 100003
        + sum(ord(ch) for ch in path)
    )

    rng = random.Random(seed_value)

    try:

        rx_range, ry_range, rz_range = get_rotation_ranges(path)

        # Use broad rotations on all three axes.
        rx = rng.uniform(-rx_range, rx_range)
        ry = rng.uniform(-ry_range, ry_range)
        rz = rng.uniform(-rz_range, rz_range)

        # Some variations include near-quarter-turn or half-turn
        # yaw changes, increasing dataset diversity.
        if rng.random() < 0.45:
            rz = rng.choice([
                -180.0, -135.0, -90.0, -45.0,
                45.0, 90.0, 135.0, 180.0
            ]) + rng.uniform(-10.0, 10.0)

        rotation_x = Gf.Rotation(
            Gf.Vec3d(1.0, 0.0, 0.0), rx
        )

        rotation_y = Gf.Rotation(
            Gf.Vec3d(0.0, 1.0, 0.0), ry
        )

        rotation_z = Gf.Rotation(
            Gf.Vec3d(0.0, 0.0, 1.0), rz
        )

        delta_rotation = (
            rotation_x * rotation_y * rotation_z
        )

        # Create a fresh transform every time from the original.
        transform = Gf.Transform(
            data["original_matrix"]
        )

        transform.SetTranslation(
            Gf.Vec3d(
                position[0],
                position[1],
                position[2]
            )
        )

        # Preserve original scale.
        transform.SetScale(data["scale"])

        # Combine the original orientation with the new rotation.
        transform.SetRotation(
            data["rotation"] * delta_rotation
        )

        # Write the complete matrix.
        data["matrix_op"].Set(
            transform.GetMatrix()
        )

        print(
            "[POSE OK] {} | Pos=({:.2f},{:.2f},{:.2f}) "
            "| Rot=({:.1f},{:.1f},{:.1f})".format(
                path,
                position[0],
                position[1],
                position[2],
                rx,
                ry,
                rz
            )
        )

    except Exception as exc:

        print(
            "[POSE ERROR] {}: {}".format(
                path, exc
            )
        )


# ============================================================
# EXISTING LIGHTS ONLY
# ============================================================

def find_existing_lights():

    supported_types = {
        "DomeLight",
        "DistantLight",
        "RectLight",
        "CylinderLight",
        "DiskLight",
    }

    lights = []

    for prim in stage.Traverse():

        if prim.GetTypeName() not in supported_types:
            continue

        intensity_attr = prim.GetAttribute("inputs:intensity")

        if not intensity_attr or not intensity_attr.IsValid():
            continue

        color_attr = prim.GetAttribute("inputs:color")

        base_intensity = intensity_attr.Get()

        if base_intensity is None:
            base_intensity = 1.0

        base_color = None

        if color_attr and color_attr.IsValid():
            base_color = color_attr.Get()

        lights.append({
            "path": str(prim.GetPath()),
            "intensity": intensity_attr,
            "base_intensity": float(base_intensity),
            "color": color_attr,
            "base_color": base_color,
        })

    print("[Lighting] Existing lights found: {}".format(
        len(lights)
    ))

    return lights


# ============================================================
# RANDOMIZE EXISTING LIGHTS
# No new lights are created.
# ============================================================

def randomize_lights(lights, variation_index):

    rng = random.Random(
        RANDOM_SEED + variation_index * 211
    )

    for light in lights:

        try:

            new_intensity = (
                light["base_intensity"]
                * rng.uniform(0.75, 1.25)
            )

            light["intensity"].Set(
                max(0.0, new_intensity)
            )

            color_attr = light["color"]
            base_color = light["base_color"]

            if (
                color_attr
                and color_attr.IsValid()
                and base_color is not None
            ):

                color = Gf.Vec3f(
                    max(0.0, min(
                        1.0,
                        float(base_color[0])
                        * rng.uniform(0.9, 1.1)
                    )),
                    max(0.0, min(
                        1.0,
                        float(base_color[1])
                        * rng.uniform(0.9, 1.1)
                    )),
                    max(0.0, min(
                        1.0,
                        float(base_color[2])
                        * rng.uniform(0.9, 1.1)
                    ))
                )

                color_attr.Set(color)

        except Exception as exc:

            print(
                "[LIGHT WARNING] {}: {}".format(
                    light["path"], exc
                )
            )


# ============================================================
# INITIALIZE RANDOMIZER
# ============================================================

materials = create_material_palette()

object_transforms = []

for path in OBJECT_PATHS:

    data = prepare_transform(path)

    if data is not None:
        object_transforms.append(data)


# Prepare camera separately.
camera_data = None

camera_prim = stage.GetPrimAtPath(CAMERA_PATH)

if (
    camera_prim.IsValid()
    and camera_prim.IsA(UsdGeom.Camera)
):

    camera_data = prepare_transform(CAMERA_PATH)

    print("[Camera] Enabled.")

else:

    print("[Camera] Not found or not a USD Camera.")


existing_lights = find_existing_lights()

print(
    "[SETUP] Transformable objects: {}".format(
        len(object_transforms)
    )
)


# ============================================================
# RANDOMIZE CAMERA
# ============================================================

def randomize_camera(data, variation_index):

    if data is None:
        return

    rng = random.Random(
        RANDOM_SEED + variation_index * 701
    )

    try:

        transform = Gf.Transform(
            data["original_matrix"]
        )

        base = data["translation"]

        transform.SetTranslation(
            Gf.Vec3d(
                base[0] + rng.uniform(-0.10, 0.10),
                base[1] + rng.uniform(-0.10, 0.10),
                base[2] + rng.uniform(-0.05, 0.05)
            )
        )

        rx = rng.uniform(-3.0, 3.0)
        ry = rng.uniform(-3.0, 3.0)
        rz = rng.uniform(-8.0, 8.0)

        delta_rotation = (
            Gf.Rotation(Gf.Vec3d(1, 0, 0), rx)
            * Gf.Rotation(Gf.Vec3d(0, 1, 0), ry)
            * Gf.Rotation(Gf.Vec3d(0, 0, 1), rz)
        )

        transform.SetRotation(
            data["rotation"] * delta_rotation
        )

        data["matrix_op"].Set(
            transform.GetMatrix()
        )

    except Exception as exc:

        print("[CAMERA ERROR] {}".format(exc))


# ============================================================
# APPLY ONE VARIATION
# ============================================================

def apply_variation(variation_index):

    print(
        "\n========== VARIATION {}/{} ==========".format(
            variation_index + 1,
            NUM_VARIATIONS
        )
    )

    # 1. Generate new object positions with spacing checks.
    positions = generate_positions(
        object_transforms,
        variation_index
    )

    # 2. Apply diverse position and orientation changes.
    for data in object_transforms:

        position = positions.get(
            data["path"],
            data["translation"]
        )

        apply_pose(
            data,
            position,
            variation_index
        )

    # 3. Randomize materials.
    for target_index, path in enumerate(MATERIAL_TARGETS):

        material_index = (
            variation_index * 7 + target_index * 3
        ) % len(materials)

        apply_material(
            path,
            materials[material_index]
        )

    # 4. Randomize existing lights only.
    randomize_lights(
        existing_lights,
        variation_index
    )

    # 5. Camera variation.
    randomize_camera(
        camera_data,
        variation_index
    )

    print(
        "========== VARIATION {} COMPLETE ==========\n"
        .format(variation_index + 1)
    )


# ============================================================
# AUTOMATIC VARIATION LOOP
# Applies a variation immediately, then every 2 seconds.
# ============================================================

async def animate_variations():

    variation_index = 0

    print(
        "[Randomizer] Starting {} variations.".format(
            NUM_VARIATIONS
        )
    )

    try:

        while True:

            if RUN_WHILE_PAUSED or timeline.is_playing():

                apply_variation(variation_index)

                variation_index = (
                    variation_index + 1
                ) % NUM_VARIATIONS

            await asyncio.sleep(
                VARIATION_INTERVAL
            )

    except asyncio.CancelledError:

        print("[Randomizer] Stopped.")
        raise

    except Exception as exc:

        print("[Randomizer ERROR] {}".format(exc))
        raise


# ============================================================
# START / RESTART TASK
# ============================================================

old_task = globals().get(
    "_hospital_randomizer_task_v2"
)

if old_task is not None and not old_task.done():
    old_task.cancel()

_hospital_randomizer_task_v2 = asyncio.ensure_future(
    animate_variations()
)

print("[Randomizer] Initialized.")
print("[Randomizer] First variation will be applied shortly.")
