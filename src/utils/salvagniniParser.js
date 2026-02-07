const DEFAULT_VARIABLES = {
  blankSizeX: "X",
  blankSizeY: "Y",
  thickness: "T",
  bendAngle: "A",
  bendSide: "S",
  bendType: "B",
  bendStop: "P",
  toolSet: "U",
};

const SIDE_ALIASES = {
  left: "X-",
  right: "X+",
  top: "Y+",
  bottom: "Y-",
  "x+": "X+",
  "x-": "X-",
  "y+": "Y+",
  "y-": "Y-",
};

const BEND_TYPE_LABELS = {
  positive: "POS",
  negative: "NEG",
  up: "POS",
  down: "NEG",
};

const AXIS_LABELS = {
  X: "X",
  Y: "Y",
};

const isNumber = (value) => typeof value === "number" && !Number.isNaN(value);

const normalizeSide = (side) => {
  if (!side) return "";
  const key = String(side).toLowerCase();
  return SIDE_ALIASES[key] || String(side).toUpperCase();
};

const normalizeBendType = (type) => {
  if (!type) return "";
  const key = String(type).toLowerCase();
  return BEND_TYPE_LABELS[key] || String(type).toUpperCase();
};

const sideAxis = (side) => {
  const normalized = normalizeSide(side);
  if (normalized.startsWith("X")) return "X";
  if (normalized.startsWith("Y")) return "Y";
  return "";
};

const stableSort = (items, compare) => {
  return items
    .map((item, index) => ({ item, index }))
    .sort((a, b) => {
      const result = compare(a.item, b.item);
      return result === 0 ? a.index - b.index : result;
    })
    .map(({ item }) => item);
};

const formatStop = (stop) => {
  if (!stop) return "";
  if (typeof stop === "string") return stop;
  const parts = [];
  if (isNumber(stop.x)) parts.push(`X=${stop.x.toFixed(2)}`);
  if (isNumber(stop.y)) parts.push(`Y=${stop.y.toFixed(2)}`);
  return parts.join(" ");
};

const defaultSortByAxis = (axisPriority) => (a, b) => {
  const axisA = sideAxis(a.side);
  const axisB = sideAxis(b.side);
  const axisIndexA = axisPriority.indexOf(axisA);
  const axisIndexB = axisPriority.indexOf(axisB);
  if (axisIndexA !== axisIndexB) return axisIndexA - axisIndexB;
  return 0;
};

export const determineAxisPriority = (blankSize) => {
  if (!blankSize || !isNumber(blankSize.x) || !isNumber(blankSize.y)) {
    return ["X", "Y"];
  }
  return blankSize.x <= blankSize.y ? ["X", "Y"] : ["Y", "X"];
};

export const buildBendSequence = (bends, options = {}) => {
  const {
    blankSize,
    groupNegativeBends = true,
    variables = DEFAULT_VARIABLES,
    toolMap = {},
  } = options;

  const axisPriority = determineAxisPriority(blankSize);
  const axisSorter = defaultSortByAxis(axisPriority);

  const normalized = bends.map((bend, index) => {
    const side = normalizeSide(bend.side || bend.face || bend.edge || "");
    const type = normalizeBendType(bend.type || bend.direction || "");
    return {
      id: bend.id ?? `${index + 1}`,
      side,
      axis: sideAxis(side),
      angle: isNumber(bend.angle) ? bend.angle : 90,
      type,
      stop: bend.stop || bend.position || "",
      toolSet: bend.toolSet || toolMap[side] || "",
      raw: bend,
    };
  });

  const sortedByAxis = stableSort(normalized, axisSorter);

  const sorted = groupNegativeBends
    ? stableSort(sortedByAxis, (a, b) => {
        const typePriority = a.type === "NEG" ? 0 : 1;
        const typePriorityB = b.type === "NEG" ? 0 : 1;
        if (typePriority !== typePriorityB) return typePriority - typePriorityB;
        return 0;
      })
    : sortedByAxis;

  return sorted.map((bend, index) => ({
    step: index + 1,
    [variables.bendSide]: bend.side,
    [variables.bendType]: bend.type,
    [variables.bendAngle]: bend.angle,
    [variables.bendStop]: formatStop(bend.stop),
    [variables.toolSet]: bend.toolSet,
    axis: AXIS_LABELS[bend.axis] || bend.axis,
    raw: bend.raw,
  }));
};

export const buildProgramMetadata = (part, options = {}) => {
  const { variables = DEFAULT_VARIABLES } = options;
  return {
    partName: part.name || "",
    material: part.material || "",
    thickness: part.thickness || "",
    [variables.blankSizeX]: part.blankSize?.x ?? "",
    [variables.blankSizeY]: part.blankSize?.y ?? "",
  };
};

export const DEFAULT_SALVAGNINI_VARIABLES = DEFAULT_VARIABLES;
