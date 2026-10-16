INSERT INTO country (iso_code, name) VALUES ('RU', 'Россия'), ('ZZ', 'Не определена');

INSERT INTO review_status (code, label) VALUES
    ('pending', 'Ожидает разбора'),
    ('confirmed_fraud', 'Мошенничество подтверждено'),
    ('false_positive', 'Ложное срабатывание'),
    ('cleared', 'Проверено, чисто');

INSERT INTO blocking_policy (name, review_threshold, auto_block_threshold,
    auto_block_enabled, false_block_cost, missed_fraud_cost, is_active)
VALUES ('Политика ML', 40, 70, TRUE, 1500, 12000, TRUE);

INSERT INTO connection_type (code, name) VALUES
    ('mobile', 'Мобильная сеть'), ('pstn', 'Фиксированная сеть'),
    ('voip', 'VoIP'), ('sip_gateway', 'SIP-шлюз'), ('roaming', 'Роуминг');
INSERT INTO call_direction (code, name) VALUES
    ('incoming', 'Входящий'), ('outgoing', 'Исходящий'), ('forwarded', 'Переадресованный');
INSERT INTO time_bucket (code, label, hour_from, hour_to) VALUES
    ('night', 'ночь, 00:00–06:00', 0, 6), ('morning', 'утро, 06:00–12:00', 6, 12),
    ('day', 'день, 12:00–18:00', 12, 18), ('evening', 'вечер, 18:00–24:00', 18, 24);
INSERT INTO number_kind (code, name) VALUES
    ('mobile', 'Мобильный'), ('landline', 'Городской'),
    ('virtual', 'Виртуальный'), ('unknown', 'Не определён');
