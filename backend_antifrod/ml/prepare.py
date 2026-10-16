"""python -m ml.prepare --input CDR_OUT --output dataset/prepared.csv"""
import argparse
import json
import logging
from pathlib import Path

from ml.data import attach_labels, load_database, load_records


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--input", help="Каталог CDR_*.cdr, один .cdr или raw.csv (разделитель ;) ")
    source.add_argument("--database", action="store_true", help="call_record + подтверждённые call_review")
    parser.add_argument("--labels", help="CSV row_hash;label;scenario (0 — легитимный, 1 — фрод)")
    parser.add_argument("--weak-labels", action="store_true", help="Предварительные сценарные метки, требуют проверки")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    try:
        frame, report = load_database() if args.database else load_records(args.input)
        frame = attach_labels(frame, args.labels)
        if args.weak_labels:
            if args.labels or args.database or ("label" in frame and frame.label.notna().any()):
                raise ValueError("Слабая разметка не должна перезаписывать существующие вердикты")
            from ml.weak_labels import label_scenarios
            weak = label_scenarios(frame)
            for column in weak:
                frame[column] = weak[column]
            report["weak_labels"] = frame.scenario.value_counts().to_dict()
            logging.warning("Созданы предварительные метки: метрики на них оценивают воспроизведение правил")
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        frame.to_csv(output, sep=";", index=False)
        output.with_suffix(".report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2))
        logging.info("Сохранено %s строк в %s", len(frame), output)
    except Exception:
        logging.exception("Подготовка данных завершилась ошибкой")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
