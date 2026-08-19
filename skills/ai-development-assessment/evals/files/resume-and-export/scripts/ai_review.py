"""ダミー実装: PR差分をAIでレビューし指摘点を出力する(evals用フィクスチャ)。"""
import argparse


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--diff", required=True)
    args = parser.parse_args()
    print(f"reviewed diff: {args.diff}")


if __name__ == "__main__":
    main()
