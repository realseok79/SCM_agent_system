package com.sigma.scm.saeie;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.sigma.scm.util.RegionStandardizer;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Component;

import java.time.LocalDate;
import java.time.format.DateTimeFormatter;
import java.time.temporal.ChronoUnit;
import java.util.*;

@Component
@RequiredArgsConstructor
public class RowValidator {

    private final RegionStandardizer regionStandardizer;
    private final ObjectMapper objectMapper = new ObjectMapper();

    public static class ValidationResult {
        public List<Map<String, Object>> payloadList = new ArrayList<>();
        public boolean hasCritical = false;
        public boolean hasError = false;
        public boolean hasWarning = false;
    }

    private LocalDate parseDate(String valStr) {
        String trimmed = valStr.trim();
        List<DateTimeFormatter> formatters = Arrays.asList(
            DateTimeFormatter.ofPattern("yyyy-MM-dd"),
            DateTimeFormatter.ofPattern("yyyy/MM/dd"),
            DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss"),
            DateTimeFormatter.ofPattern("yyyy/MM/dd HH:mm:ss")
        );

        for (DateTimeFormatter fmt : formatters) {
            try {
                return LocalDate.parse(trimmed, fmt);
            } catch (Exception ignored) {}
        }
        // Fallback for short timestamp or custom ISO date formats
        try {
            if (trimmed.length() >= 10) {
                return LocalDate.parse(trimmed.substring(0, 10));
            }
        } catch (Exception ignored) {}

        throw new IllegalArgumentException("Invalid date format: " + valStr);
    }

    public ValidationResult validateRows(
            List<List<String>> rows,
            List<String> rawHeaders,
            Map<String, String> mapping,
            String companyId) {

        int MAX_VALIDATION_PAYLOAD_BYTES = 2097152; // 2MB
        ValidationResult result = new ValidationResult();

        // Invert mapping: standard SCM columns -> raw headers
        Map<String, String> invMapping = new HashMap<>();
        for (Map.Entry<String, String> entry : mapping.entrySet()) {
            if (entry.getValue() != null) {
                invMapping.put(entry.getValue(), entry.getKey());
            }
        }

        List<String> requiredCols = Arrays.asList("region_code", "product_name", "date", "quantity");
        LocalDate now = LocalDate.now();

        for (int idx = 0; idx < rows.size(); idx++) {
            List<String> row = rows.get(idx);
            
            // Map row to headers
            Map<String, String> rawRowData = new LinkedHashMap<>();
            for (int i = 0; i < rawHeaders.size(); i++) {
                String header = rawHeaders.get(i);
                String val = i < row.size() ? row.get(i) : null;
                rawRowData.put(header, val);
            }

            List<Map<String, String>> rowErrors = new ArrayList<>();
            Map<String, Object> standardizedValues = new LinkedHashMap<>();
            standardizedValues.put("region_code", null);
            standardizedValues.put("product_name", null);
            standardizedValues.put("date", null);
            standardizedValues.put("quantity", null);
            standardizedValues.put("company_id", companyId);
            standardizedValues.put("warehouse_code", null);

            // Check required SCM standard columns existence in mapping
            for (String req : requiredCols) {
                if (!invMapping.containsKey(req)) {
                    Map<String, String> err = new HashMap<>();
                    err.put("severity", "CRITICAL");
                    err.put("message", "Required column '" + req + "' is missing in header mapping.");
                    err.put("column", req);
                    rowErrors.add(err);
                    result.hasCritical = true;
                }
            }

            if (!result.hasCritical) {
                // 1. region_code
                String rawH = invMapping.get("region_code");
                String rawVal = rawRowData.get(rawH);
                if (rawVal == null || rawVal.trim().isEmpty()) {
                    Map<String, String> err = new HashMap<>();
                    err.put("severity", "CRITICAL");
                    err.put("message", "Required column 'region_code' is null or empty.");
                    err.put("column", "region_code");
                    rowErrors.add(err);
                    result.hasCritical = true;
                } else {
                    try {
                        String stdRegionCode = regionStandardizer.standardize(rawVal.trim());
                        standardizedValues.put("region_code", stdRegionCode);
                    } catch (Exception e) {
                        Map<String, String> err = new HashMap<>();
                        err.put("severity", "CRITICAL");
                        err.put("message", e.getMessage());
                        err.put("column", "region_code");
                        rowErrors.add(err);
                        result.hasCritical = true;
                    }
                }

                // 2. product_name
                rawH = invMapping.get("product_name");
                rawVal = rawRowData.get(rawH);
                if (rawVal == null || rawVal.trim().isEmpty()) {
                    Map<String, String> err = new HashMap<>();
                    err.put("severity", "CRITICAL");
                    err.put("message", "Required column 'product_name' is null or empty.");
                    err.put("column", "product_name");
                    rowErrors.add(err);
                    result.hasCritical = true;
                } else {
                    String prodStr = rawVal.trim();
                    if (prodStr.equalsIgnoreCase("nan") || prodStr.isEmpty()) {
                        Map<String, String> err = new HashMap<>();
                        err.put("severity", "CRITICAL");
                        err.put("message", "Product name is empty or invalid.");
                        err.put("column", "product_name");
                        rowErrors.add(err);
                        result.hasCritical = true;
                    } else {
                        standardizedValues.put("product_name", prodStr);
                    }
                }

                // 3. date
                rawH = invMapping.get("date");
                rawVal = rawRowData.get(rawH);
                if (rawVal == null || rawVal.trim().isEmpty()) {
                    Map<String, String> err = new HashMap<>();
                    err.put("severity", "CRITICAL");
                    err.put("message", "Required column 'date' is null or empty.");
                    err.put("column", "date");
                    rowErrors.add(err);
                    result.hasCritical = true;
                } else {
                    try {
                        LocalDate dateObj = parseDate(rawVal);
                        long daysDiff = ChronoUnit.DAYS.between(now, dateObj);
                        double diffYears = (double) daysDiff / 365.25;

                        if (diffYears > 1.0) {
                            Map<String, String> err = new HashMap<>();
                            err.put("severity", "ERROR");
                            err.put("message", "Date is more than 1 year in the future.");
                            err.put("column", "date");
                            rowErrors.add(err);
                            result.hasError = true;
                        } else if (diffYears < -5.0) {
                            Map<String, String> err = new HashMap<>();
                            err.put("severity", "WARNING");
                            err.put("message", "Date is older than 5 years.");
                            err.put("column", "date");
                            rowErrors.add(err);
                            result.hasWarning = true;
                        }

                        standardizedValues.put("date", dateObj.format(DateTimeFormatter.ofPattern("yyyy-MM-dd")));
                    } catch (Exception e) {
                        Map<String, String> err = new HashMap<>();
                        err.put("severity", "CRITICAL");
                        err.put("message", "Failed to parse date: " + e.getMessage());
                        err.put("column", "date");
                        rowErrors.add(err);
                        result.hasCritical = true;
                    }
                }

                // 4. quantity
                rawH = invMapping.get("quantity");
                rawVal = rawRowData.get(rawH);
                if (rawVal == null || rawVal.trim().isEmpty()) {
                    Map<String, String> err = new HashMap<>();
                    err.put("severity", "CRITICAL");
                    err.put("message", "Required column 'quantity' is null or empty.");
                    err.put("column", "quantity");
                    rowErrors.add(err);
                    result.hasCritical = true;
                } else {
                    try {
                        double qty = Double.parseDouble(rawVal.trim());
                        double rounded = Math.round(qty);
                        if (Math.abs(qty - rounded) > 1e-9) {
                            Map<String, String> err = new HashMap<>();
                            err.put("severity", "WARNING");
                            err.put("message", "Fractional quantity " + qty + " rounded to nearest integer " + (int)rounded + ".");
                            err.put("column", "quantity");
                            rowErrors.add(err);
                            result.hasWarning = true;
                            qty = rounded;
                        }

                        if (qty < 0) {
                            Map<String, String> err = new HashMap<>();
                            err.put("severity", "ERROR");
                            err.put("message", "Quantity cannot be negative.");
                            err.put("column", "quantity");
                            rowErrors.add(err);
                            result.hasError = true;
                        } else if (qty >= 1000000) {
                            Map<String, String> err = new HashMap<>();
                            err.put("severity", "ERROR");
                            err.put("message", "Quantity exceeds limit of 1,000,000.");
                            err.put("column", "quantity");
                            rowErrors.add(err);
                            result.hasError = true;
                        }

                        standardizedValues.put("quantity", qty);
                    } catch (NumberFormatException e) {
                        Map<String, String> err = new HashMap<>();
                        err.put("severity", "CRITICAL");
                        err.put("message", "Failed to cast quantity '" + rawVal + "' to float.");
                        err.put("column", "quantity");
                        rowErrors.add(err);
                        result.hasCritical = true;
                    }
                }

                // 5. warehouse_code (Optional)
                if (invMapping.containsKey("warehouse_code")) {
                    rawH = invMapping.get("warehouse_code");
                    rawVal = rawRowData.get(rawH);
                    if (rawVal != null) {
                        standardizedValues.put("warehouse_code", rawVal.trim());
                    }
                }
            }

            // Update result flags based on current row errors
            for (Map<String, String> err : rowErrors) {
                String sev = err.get("severity");
                if ("CRITICAL".equals(sev)) result.hasCritical = true;
                if ("ERROR".equals(sev)) result.hasError = true;
                if ("WARNING".equals(sev)) result.hasWarning = true;
            }

            Map<String, Object> payloadRow = new LinkedHashMap<>();
            payloadRow.put("source_row_index", idx);
            payloadRow.put("standardized_values", standardizedValues);
            payloadRow.put("raw_row_data", rawRowData);
            payloadRow.put("validation_errors", rowErrors);
            result.payloadList.add(payloadRow);
        }

        // Enforce 2MB size limit
        try {
            byte[] bytes = objectMapper.writeValueAsBytes(result.payloadList);
            if (bytes.length > MAX_VALIDATION_PAYLOAD_BYTES) {
                throw new SaeieException.ValidationPayloadTooLargeException(
                    "Validation payload size (" + bytes.length + " bytes) exceeds maximum limit of 2MB."
                );
            }
        } catch (SaeieException e) {
            throw e;
        } catch (Exception e) {
            throw new RuntimeException("Jackson serialization error", e);
        }

        return result;
    }
}
