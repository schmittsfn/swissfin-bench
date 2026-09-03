
import json
import sys
import argparse
import pandas as pd
import yaml

from bench.parser import Parser
from bench.router import ModelProviderType
from bench.database import Database
from bench.runner import Runner

print("Total arguments:", len(sys.argv))
print("Script name:", sys.argv[0])
print("Arguments:", sys.argv[1:])

def main():
    """The main function of the script."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--database",
        help=(
            "SQLite database path. Overrides SWISSFIN_DB_PATH; "
            "defaults to myfile.db."
        ),
    )
    subparsers = parser.add_subparsers(dest="command")

    input_parser = subparsers.add_parser("input", help="Parse one or more input files")
    input_parser.add_argument("paths", nargs='+', help="Paths to the input files (JSON, CSV, Excel, or YAML)")

    run_parser = subparsers.add_parser("run", help="Launch a benchmark run")
    run_parser.add_argument("model_provider", help="Provider identifier")
    run_parser.add_argument("model_name", help="Provider model identifier")
    run_parser.add_argument(
        "--label",
        help=(
            "Optional database/display label when it must differ from the "
            "provider model identifier"
        ),
    )

    args = parser.parse_args()
    print("Parsed arguments:", args)

    with Database(path=args.database) as database:
        if args.command == "input":
            print("Input:", args.paths)
            parser = Parser(database=database)

            for _input in args.paths:
                if _input.endswith(".json"):
                    with open(_input, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        print("Loaded JSON data:", data)
                        parser.parse(data)
                elif _input.endswith(".csv"):
                    df = pd.read_csv(_input)
                    print("Loaded CSV data:")
                    print(df)
                    parser.parse(df.to_dict(orient="records"))
                elif _input.endswith(".xlsx"):
                    df = pd.read_excel(_input)
                    print("Loaded Excel data:")
                    print(df)
                    parser.parse(df.to_dict(orient="records"))
                elif _input.endswith(".yaml") or _input.endswith(".yml"):
                    with open(_input, "r", encoding="utf-8") as f:
                        data = yaml.safe_load(f)
                        print("Loaded YAML data:", data)
                        parser.parse(data)
                else:
                    print("Input file format not supported.")
        elif args.command == "run":
            print("Run:", args.model_provider, args.model_name)
            model_provider_raw: str = args.model_provider
            model_provider: ModelProviderType
            try:
                model_provider = ModelProviderType(model_provider_raw)
            except ValueError:
                print(f"Invalid model provider: {model_provider_raw}. Supported providers are: {[e.value for e in ModelProviderType]}")
                return

            runner = Runner(
                database=database,
                model_provider=model_provider,
                model_name=args.model_name,
                model_label=args.label,
            )
            response = runner.run()
            return response
        else:
            parser.print_help()

if __name__ == "__main__":
    main()
