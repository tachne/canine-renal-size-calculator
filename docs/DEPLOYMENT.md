# Streamlit Community Cloud 公開手順

2026-11-21時点の公式手順を確認した公開準備資料です。このパッケージの作成時点では、GitHubへのアップロードもCloudへのデプロイも行っていません。

## 公開前の最終確認

- 公開用ソース、原著の書誌表示、未解決SEの表示、CT適用限界、入力情報の取り扱いを管理者が確認する。
- GitHubの所有アカウント・リポジトリ名、アプリ名、公開URLの希望を決める。候補名は `vars-renal-size-reference`。名称・URLの取得可否は未確認。
- コードのライセンス方針を決める。準備版にLICENSEは付与していない。
- **公開専用ZIPを新しいフォルダに展開し、その中身だけを使用する。研究フォルダ全体や以前の解析ZIPはアップロードしない。** 公開用ZIPには過去のGit履歴も含めない。
- `PUBLIC_MANIFEST.json` のファイル一覧とSHA-256を照合する。個体別データ、Excel、原稿、画像、APIキー、Secretsを追加しない。
- 正常異常の判定を行わないこと、探索的予測帯が初期非表示であることを確認する。

## 1. GitHubに新規リポジトリを作成

GitHubの **New repository** で所有者・名前・公開範囲を選ぶ。Cloudから使用するアカウントには、このリポジトリの管理者権限が必要。既存VARSリポジトリを公開に切り替える操作は行わない。[GitHubの作成手順](https://docs.github.com/en/repositories/creating-and-managing-repositories/creating-a-new-repository)、[StreamlitのGitHub接続条件](https://docs.streamlit.io/deploy/streamlit-community-cloud/get-started/connect-your-github-account)

公開時は新規リポジトリを **Public** とし、準備済みファイルをアップロードする。新規作成画面でREADME・.gitignoreの自動生成は不要。空のリポジトリでは「uploading an existing file」、ファイルがある場合は **Add file → Upload files** を利用する。[GitHubのアップロード手順](https://docs.github.com/en/repositories/working-with-files/managing-files/adding-a-file-to-a-repository)

展開したフォルダの**中身**を配置する。ZIPそのものを置くのではなく、リポジトリ直下に `streamlit_app.py` が見える状態にする。Macでは隠しファイル表示（Command + Shift + .）を有効にし、`.streamlit/config.toml` と `.gitignore` も含める。アップロード画面でこれらが省かれた場合は、GitHubの **Add file → Create new file** で同じパス・内容を作成する。秘密情報の入力は不要。

主な構成：

```text
streamlit_app.py
renal_calculator.py
requirements.txt
.streamlit/config.toml
.gitignore
assets/model.json
assets/exploratory_prediction_grid.csv
assets/reference_predictions.csv
tests/test_public_app.py
README.md
CHANGELOG.md
PUBLIC_MANIFEST.json
docs/...
```

ブランチを `main` としてコミットする。異なるブランチ名を選んだ場合は次のCloud設定も実際の名前に合わせる。

## 2. Community Cloudに接続して配置

[Streamlit Community Cloud](https://share.streamlit.io/) にサインインし、GitHub連携を行う。GitHubの認証や権限許可は所有者が行う。[公式接続手順](https://docs.streamlit.io/deploy/streamlit-community-cloud/get-started/connect-your-github-account)

**Create app → Yup, I have an app** へ進み、次を入力する。

|設定|値|
|---|---|
|Repository|所有者アカウント／作成したリポジトリ|
|Branch|`main`（または実際にコミットしたブランチ）|
|Main file path|`streamlit_app.py`|
|App URL|希望するサブドメイン。利用できなければ別名を選ぶ|
|Advanced settings → Python version|**3.12**|
|Secrets|空欄。APIキー等は不要|

Advanced settingsを保存し、デプロイを開始する。依存関係はルートの `requirements.txt` から導入される。Rや原データは必要ない。[公式デプロイ手順](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy)、[依存関係の公式説明](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/app-dependencies)

公開リポジトリからのアプリは既定で公開になる。配置前に公開物の確認を終える。配置後は **Settings → Sharing** でも公開範囲を確認する。[公開・共有設定](https://docs.streamlit.io/deploy/streamlit-community-cloud/share-your-app)

## 3. Cloud上の最終動作確認

CloudはLinuxで稼働するため、ローカル検証とは別に次を確認する。

1. ビルドログに依存関係・起動エラーがなく、ページが表示される。
2. 初回は10 kg・左腎、実測値は空欄、予測帯は非表示。`assets/reference_predictions.csv` の10 kg予測値と表示が丸めの範囲で一致する。
3. 左右切替、体重変更、実測値入力・消去、比・曲線の更新ができる。左右を往復して入力が保たれる。
4. 1 kg・50 kgでは外挿注意を表示し、任意に予測帯を表示すると探索的であることが明示される。50 kgの位置まで予測帯は延長されない。
5. 基礎研究、モデル版、CTの適用限界、SE不一致、入力情報の説明が表示される。
6. 別のブラウザー／プライベートウィンドウでは前の利用者の入力が現れない。
7. スマートフォンで入力欄、表、4グラフが読める。匿名の閲覧者でも意図した公開URLを開ける。

Cloudでの確認日・URL・公開コミットIDを別途記録してからURLを案内する。今回の準備では、Cloud上のビルドや匿名アクセスの成功までは確認していない。

## 更新時

Cloudは接続したブランチの変更を反映するため、公開ブランチへ変更を入れる前にローカルテストと配布対象の確認を行う。計算式・係数を更新する場合はモデル版を変更し、由来と検証結果を記録する。[公式の更新動作](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy)
