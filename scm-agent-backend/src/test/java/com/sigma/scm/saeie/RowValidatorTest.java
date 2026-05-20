package com.sigma.scm.saeie;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import java.time.LocalDate;
import java.time.format.DateTimeFormatter;
import java.util.*;

import static org.junit.jupiter.api.Assertions.*;

public class RowValidatorTest {

    private RowValidator validator;

    @BeforeEach
    public void setUp() {
        validator = new RowValidator(new com.sigma.scm.util.RegionStandardizer());
    }

    @Test
    public void testValidRowValidation() {
        List<List<String>> rows = new ArrayList<>();
        rows.add(Arrays.asList("KR-11", "Mask", "2026-05-19", "500"));

        List<String> columns = Arrays.asList("지점코드", "품목명", "날짜", "수량");
        Map<String, String> mapping = new HashMap<>();
        mapping.put("지점코드", "region_code");
        mapping.put("품목명", "product_name");
        mapping.put("날짜", "date");
        mapping.put("수량", "quantity");

        RowValidator.ValidationResult result = validator.validateRows(rows, columns, mapping, "COMPANY_SIGMA");
        assertFalse(result.hasCritical);
        assertFalse(result.hasError);
        assertEquals(1, result.payloadList.size());
    }

    @Test
    public void testFutureDateError() {
        LocalDate farFuture = LocalDate.now().plusYears(2);
        String futureStr = farFuture.format(DateTimeFormatter.ISO_LOCAL_DATE);

        List<List<String>> rows = new ArrayList<>();
        rows.add(Arrays.asList("KR-11", "Mask", futureStr, "500"));

        List<String> columns = Arrays.asList("지점코드", "품목명", "날짜", "수량");
        Map<String, String> mapping = new HashMap<>();
        mapping.put("지점코드", "region_code");
        mapping.put("품목명", "product_name");
        mapping.put("날짜", "date");
        mapping.put("수량", "quantity");

        RowValidator.ValidationResult result = validator.validateRows(rows, columns, mapping, "COMPANY_SIGMA");
        assertTrue(result.hasError);
    }

    @Test
    public void testFractionalQuantityRoundingWarning() {
        List<List<String>> rows = new ArrayList<>();
        rows.add(Arrays.asList("KR-11", "Mask", "2026-05-19", "12.7"));

        List<String> columns = Arrays.asList("지점코드", "품목명", "날짜", "수량");
        Map<String, String> mapping = new HashMap<>();
        mapping.put("지점코드", "region_code");
        mapping.put("품목명", "product_name");
        mapping.put("날짜", "date");
        mapping.put("수량", "quantity");

        RowValidator.ValidationResult result = validator.validateRows(rows, columns, mapping, "COMPANY_SIGMA");
        assertTrue(result.hasWarning);
        
        // Assert float rounded to integer
        Map<String, Object> stdVals = (Map<String, Object>) result.payloadList.get(0).get("standardized_values");
        assertEquals(13.0, stdVals.get("quantity"));
    }

    @Test
    public void testExtremeQuantityError() {
        List<List<String>> rows = new ArrayList<>();
        rows.add(Arrays.asList("KR-11", "Mask", "2026-05-19", "1000001")); // Exceeds 1,000,000 limit

        List<String> columns = Arrays.asList("지점코드", "품목명", "날짜", "수량");
        Map<String, String> mapping = new HashMap<>();
        mapping.put("지점코드", "region_code");
        mapping.put("품목명", "product_name");
        mapping.put("날짜", "date");
        mapping.put("수량", "quantity");

        RowValidator.ValidationResult result = validator.validateRows(rows, columns, mapping, "COMPANY_SIGMA");
        assertTrue(result.hasError);
    }

    @Test
    public void testPayloadSizeLimitBreach() {
        // Construct lists of rows to breach the 2MB memory threshold (each row has large text)
        List<List<String>> rows = new ArrayList<>();
        char[] largeChars = new char[50000];
        Arrays.fill(largeChars, 'X');
        String superLongStr = new String(largeChars);

        for (int i = 0; i < 45; i++) { // 45 * 50KB = ~2.2MB
            rows.add(Arrays.asList("KR-11", superLongStr, "2026-05-19", "100"));
        }

        List<String> columns = Arrays.asList("지점코드", "품목명", "날짜", "수량");
        Map<String, String> mapping = new HashMap<>();
        mapping.put("지점코드", "region_code");
        mapping.put("품목명", "product_name");
        mapping.put("날짜", "date");
        mapping.put("수량", "quantity");

        assertThrows(SaeieException.ValidationPayloadTooLargeException.class, () -> {
            validator.validateRows(rows, columns, mapping, "COMPANY_SIGMA");
        });
    }
}
