INSERT INTO regions (region_name, region_code, description)
VALUES 
    ('호남권물류', '호남권물류CENTER-GLOBAL', '호남권 통합 물류 허브'),
    ('경남', '경남-GLOBAL', '경남권 물류 센터')
ON CONFLICT (region_code) DO NOTHING;
