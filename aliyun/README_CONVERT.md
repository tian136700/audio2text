# 识别文本转 PDF/Word 工具

## 功能说明

将阿里云语音识别的文本结果转换为 PDF 或 Word 格式，并调整格式：
- **说话人和时间**放在上面一行（蓝色、加粗）
- **说话内容**放在下面一行（带缩进）

## 安装依赖

```bash
pip install python-docx reportlab
```

或者使用项目的 requirements.txt：

```bash
pip install -r requirements.txt
```

## 使用方法

### 命令行使用

```bash
# 转换为 Word 格式（默认）
python aliyun/convert_to_doc.py aliyun/results/识别文本_20260108_032840.txt

# 转换为 Word 格式（指定格式）
python aliyun/convert_to_doc.py aliyun/results/识别文本_20260108_032840.txt docx

# 转换为 PDF 格式
python aliyun/convert_to_doc.py aliyun/results/识别文本_20260108_032840.txt pdf

# 指定输出路径
python aliyun/convert_to_doc.py aliyun/results/识别文本_20260108_032840.txt docx output.docx
```

### Python 代码中使用

```python
from aliyun.convert_to_doc import convert_to_word, convert_to_pdf

# 转换为 Word
word_path = convert_to_word('aliyun/results/识别文本_20260108_032840.txt')
print(f"Word 文件已生成: {word_path}")

# 转换为 PDF
pdf_path = convert_to_pdf('aliyun/results/识别文本_20260108_032840.txt')
print(f"PDF 文件已生成: {pdf_path}")
```

## 输出格式

转换后的文档格式如下：

```
[13.76秒 - 17.24秒] 说话人A
    正在为您接通，请稍后。

[2分3.36秒 - 2分6.68秒] 说话人A
    正在为你接通，请稍后。

[2分14.02秒 - 2分15.58秒] 说话人B
    Thank titrage.
```

其中：
- 时间和说话人使用蓝色、加粗字体
- 说话内容有缩进，便于阅读

## 注意事项

1. 确保已安装所需的库（python-docx 和 reportlab）
2. 输入文件必须是阿里云识别生成的文本格式
3. 输出文件会保存在与输入文件相同的目录下（除非指定了输出路径）


## 功能说明

将阿里云语音识别的文本结果转换为 PDF 或 Word 格式，并调整格式：
- **说话人和时间**放在上面一行（蓝色、加粗）
- **说话内容**放在下面一行（带缩进）

## 安装依赖

```bash
pip install python-docx reportlab
```

或者使用项目的 requirements.txt：

```bash
pip install -r requirements.txt
```

## 使用方法

### 命令行使用

```bash
# 转换为 Word 格式（默认）
python aliyun/convert_to_doc.py aliyun/results/识别文本_20260108_032840.txt

# 转换为 Word 格式（指定格式）
python aliyun/convert_to_doc.py aliyun/results/识别文本_20260108_032840.txt docx

# 转换为 PDF 格式
python aliyun/convert_to_doc.py aliyun/results/识别文本_20260108_032840.txt pdf

# 指定输出路径
python aliyun/convert_to_doc.py aliyun/results/识别文本_20260108_032840.txt docx output.docx
```

### Python 代码中使用

```python
from aliyun.convert_to_doc import convert_to_word, convert_to_pdf

# 转换为 Word
word_path = convert_to_word('aliyun/results/识别文本_20260108_032840.txt')
print(f"Word 文件已生成: {word_path}")

# 转换为 PDF
pdf_path = convert_to_pdf('aliyun/results/识别文本_20260108_032840.txt')
print(f"PDF 文件已生成: {pdf_path}")
```

## 输出格式

转换后的文档格式如下：

```
[13.76秒 - 17.24秒] 说话人A
    正在为您接通，请稍后。

[2分3.36秒 - 2分6.68秒] 说话人A
    正在为你接通，请稍后。

[2分14.02秒 - 2分15.58秒] 说话人B
    Thank titrage.
```

其中：
- 时间和说话人使用蓝色、加粗字体
- 说话内容有缩进，便于阅读

## 注意事项

1. 确保已安装所需的库（python-docx 和 reportlab）
2. 输入文件必须是阿里云识别生成的文本格式
3. 输出文件会保存在与输入文件相同的目录下（除非指定了输出路径）


## 功能说明

将阿里云语音识别的文本结果转换为 PDF 或 Word 格式，并调整格式：
- **说话人和时间**放在上面一行（蓝色、加粗）
- **说话内容**放在下面一行（带缩进）

## 安装依赖

```bash
pip install python-docx reportlab
```

或者使用项目的 requirements.txt：

```bash
pip install -r requirements.txt
```

## 使用方法

### 命令行使用

```bash
# 转换为 Word 格式（默认）
python aliyun/convert_to_doc.py aliyun/results/识别文本_20260108_032840.txt

# 转换为 Word 格式（指定格式）
python aliyun/convert_to_doc.py aliyun/results/识别文本_20260108_032840.txt docx

# 转换为 PDF 格式
python aliyun/convert_to_doc.py aliyun/results/识别文本_20260108_032840.txt pdf

# 指定输出路径
python aliyun/convert_to_doc.py aliyun/results/识别文本_20260108_032840.txt docx output.docx
```

### Python 代码中使用

```python
from aliyun.convert_to_doc import convert_to_word, convert_to_pdf

# 转换为 Word
word_path = convert_to_word('aliyun/results/识别文本_20260108_032840.txt')
print(f"Word 文件已生成: {word_path}")

# 转换为 PDF
pdf_path = convert_to_pdf('aliyun/results/识别文本_20260108_032840.txt')
print(f"PDF 文件已生成: {pdf_path}")
```

## 输出格式

转换后的文档格式如下：

```
[13.76秒 - 17.24秒] 说话人A
    正在为您接通，请稍后。

[2分3.36秒 - 2分6.68秒] 说话人A
    正在为你接通，请稍后。

[2分14.02秒 - 2分15.58秒] 说话人B
    Thank titrage.
```

其中：
- 时间和说话人使用蓝色、加粗字体
- 说话内容有缩进，便于阅读

## 注意事项

1. 确保已安装所需的库（python-docx 和 reportlab）
2. 输入文件必须是阿里云识别生成的文本格式
3. 输出文件会保存在与输入文件相同的目录下（除非指定了输出路径）


