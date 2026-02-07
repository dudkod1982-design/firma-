import React from "react";
import {
  Document,
  Page,
  Text,
  View,
  StyleSheet,
} from "@react-pdf/renderer";

const styles = StyleSheet.create({
  page: {
    padding: 24,
    fontSize: 10,
    fontFamily: "Helvetica",
    color: "#111",
  },
  header: {
    marginBottom: 12,
  },
  title: {
    fontSize: 16,
    fontWeight: 700,
  },
  metadataRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    marginTop: 6,
  },
  metadataItem: {
    width: "48%",
  },
  label: {
    fontSize: 9,
    color: "#555",
  },
  value: {
    fontSize: 11,
    fontWeight: 600,
  },
  table: {
    borderWidth: 1,
    borderColor: "#222",
    borderStyle: "solid",
  },
  tableRow: {
    flexDirection: "row",
  },
  tableHeader: {
    backgroundColor: "#f1f1f1",
    borderBottomWidth: 1,
    borderBottomColor: "#222",
    borderBottomStyle: "solid",
  },
  cell: {
    paddingVertical: 4,
    paddingHorizontal: 6,
    borderRightWidth: 1,
    borderRightColor: "#222",
    borderRightStyle: "solid",
  },
  cellLast: {
    borderRightWidth: 0,
  },
  headerText: {
    fontWeight: 700,
  },
});

const columnConfig = [
  { key: "step", label: "Step #", width: "8%" },
  { key: "S", label: "Side", width: "14%" },
  { key: "B", label: "Bend Type", width: "16%" },
  { key: "A", label: "Angle", width: "12%" },
  { key: "P", label: "Stop", width: "28%" },
  { key: "U", label: "Tool Set", width: "22%" },
];

const resolveValue = (row, key) => {
  if (key === "step") return row.step;
  return row[key] ?? "";
};

const ProgramTable = ({ rows, columns = columnConfig }) => (
  <View style={styles.table}>
    <View style={[styles.tableRow, styles.tableHeader]}>
      {columns.map((col, index) => (
        <View
          key={col.key}
          style={[
            styles.cell,
            { width: col.width },
            index === columns.length - 1 && styles.cellLast,
          ]}
        >
          <Text style={styles.headerText}>{col.label}</Text>
        </View>
      ))}
    </View>
    {rows.map((row) => (
      <View key={row.step} style={styles.tableRow}>
        {columns.map((col, index) => (
          <View
            key={`${row.step}-${col.key}`}
            style={[
              styles.cell,
              { width: col.width },
              index === columns.length - 1 && styles.cellLast,
            ]}
          >
            <Text>{resolveValue(row, col.key)}</Text>
          </View>
        ))}
      </View>
    ))}
  </View>
);

const ProgramSheetGenerator = ({
  programRows = [],
  metadata = {},
  variables = {},
}) => {
  const displayVariables = {
    blankSizeX: variables.blankSizeX || "X",
    blankSizeY: variables.blankSizeY || "Y",
    thickness: variables.thickness || "T",
  };

  return (
    <Document>
      <Page size="A4" style={styles.page}>
        <View style={styles.header}>
          <Text style={styles.title}>Salvagnini P4 Program Sheet</Text>
          <View style={styles.metadataRow}>
            <View style={styles.metadataItem}>
              <Text style={styles.label}>Part Name</Text>
              <Text style={styles.value}>{metadata.partName || ""}</Text>
            </View>
            <View style={styles.metadataItem}>
              <Text style={styles.label}>Material</Text>
              <Text style={styles.value}>{metadata.material || ""}</Text>
            </View>
          </View>
          <View style={styles.metadataRow}>
            <View style={styles.metadataItem}>
              <Text style={styles.label}>Thickness ({displayVariables.thickness})</Text>
              <Text style={styles.value}>{metadata.thickness || ""}</Text>
            </View>
            <View style={styles.metadataItem}>
              <Text style={styles.label}>
                Blank Size ({displayVariables.blankSizeX} x {displayVariables.blankSizeY})
              </Text>
              <Text style={styles.value}>
                {metadata[displayVariables.blankSizeX] || ""} x {metadata[displayVariables.blankSizeY] || ""}
              </Text>
            </View>
          </View>
        </View>
        <ProgramTable rows={programRows} />
      </Page>
    </Document>
  );
};

export default ProgramSheetGenerator;
