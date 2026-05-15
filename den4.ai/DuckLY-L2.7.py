# DuckLY-L2.5: Local Agentic Voice Assistant
# Copyright (C) 2026 Denis Bdoyan

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

# Contact information:
# - Email: denisbdoyan@yandex.ru


import tkinter as tk
from tkinter import Entry, Button, Label
from tkinter import ttk
from pathlib import Path
from ctypes import wintypes
import urllib.request
import ctypes
import json
import threading
import subprocess
import platform
import base64
import os
import re
import struct
import time
import codecs


STATE_FILE = "duckly_state.json"
MAX_HISTORY = 100


messages_list = []


def save_state():
    api_key = load_api_key()

    model = "DezzyWxL/legacy_audio:latest"
    if 'application' in globals() and application is not None:
        try:
            model = application.model_var.get()
        except Exception:
            pass

    state = {
        "messages": messages_list,
        "api_key": api_key,
        "model": model
    }
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def load_state():
    if not os.path.exists(STATE_FILE):
        return None
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        return None


def load_api_key():
    try:
        if os.path.exists("api_key.txt"):
            with open("api_key.txt", "r", encoding="utf-8") as f:
                key = f.read().strip()
                return key if key else ""
    except Exception:
        pass
    return ""

def save_api_key(key):
    try:
        with open("api_key.txt", "w", encoding="utf-8") as f:
            f.write(key.strip())
    except Exception:
        pass

def is_ollama_running():
    try:
        urllib.request.urlopen("http://localhost:11434", timeout=5)
        return True
    except Exception:
        return False


def search_web(query):
    api_key = application.api_key_entry.get().strip()
    if not api_key or api_key == "Введите ключ...":
        return "❌ Не указан API-ключ для Ollama. Пользователь должен ввести его в поле '🔑 API Ключ'."

    raw_text = ""
    base_url = "https://ollama.com/api/web_search"
    req = urllib.request.Request(
        base_url,
        headers={"Authorization": f"Bearer {api_key}"},
        data=json.dumps({"query": query}).encode(),
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            main_chunk = data["results"][0]
            title = main_chunk["title"]
            content = main_chunk["content"]
            if title and content:
                return f"\n\n📌\n{title}\n📘\n{content}\n\n"[:4096]

    except Exception as e:
        return f"❌ Ошибка поиска: {e}"


def get_cwd():
    return str(Path.cwd())


def list_files(path="."):
    try:
        p = Path(path)
        if not p.exists():
            return f"Ошибка: путь '{path}' не существует."
        items = []
        for item in p.iterdir():
            kind = "📁" if item.is_dir() else "📄"
            items.append(f"{kind} {item.name}")
        return "\n".join(sorted(items)) if items else "Пустая директория."
    except Exception as e:
        return f"Ошибка при чтении директории: {e}"


def read_file(filename):
    try:
        with open(filename, "r", encoding="utf-8") as f:
            content = f.read()
        return f"✅ Содержимое файла `{filename}`:\n\n{content}"
    except FileNotFoundError:
        return f"❌ Файл `{filename}` не найден."
    except PermissionError:
        return f"❌ Нет доступа к файлу `{filename}`."
    except Exception as e:
        return f"Ошибка при чтении файла: {e}"


def write_file(name, content):
    try:
        with open(name, "w", encoding="utf-8") as f:
            f.write(content)
        return f"✅ Файл `{name}` успешно создан/перезаписан."
    except Exception as e:
        return f"Ошибка при создании файла: {e}"


def edit_file(filename, old_content, new_content):
    try:
        with open(filename, "r", encoding="utf-8") as f:
            text = f.read()
        if old_content not in text:
            return f"❌ Текст для замены не найден в `{filename}`."
        updated = text.replace(old_content, new_content, 1)
        with open(filename, "w", encoding="utf-8") as f:
            f.write(updated)
        return (
            f"✅ Обновлено в `{filename}`:\n"
            f"Заменено:\n```\n{old_content}\n```\n"
            f"На:\n```\n{new_content}\n```"
        )
    except FileNotFoundError:
        return f"❌ Файл `{filename}` не найден."
    except Exception as e:
        return f"Ошибка при редактировании: {e}"


def create_dir(path):
    try:
        Path(path).mkdir(parents=True, exist_ok=True)
        return f"✅ Папка `{path}` создана."
    except Exception as e:
        return f"Ошибка при создании папки: {e}"


def delete_file(path):
    try:
        os.remove(path)
        return f"🗑️ Файл `{path}` удалён."
    except Exception as e:
        return f"❌ Не удалось удалить файл `{path}`: {e}."


def delete_dir(path):
    if os.path.exists(path):
        if os.path.isdir(path):
            try:
                os.rmdir(path)
                return f"🗑️ Папка `{path}` удалена."
            except Exception as e:
                return f"❌ Не удалось удалить папку `{path}`: {e}."
        else:
            return f"❌ `{path}` не является папкой."
    else:
        return f"❌ Папка `{path}` не существует."


def _write_wave_pcm(path, pcm_data, *, sample_rate, channels, sampwidth):
    byte_rate = sample_rate * channels * sampwidth
    block_align = channels * sampwidth
    bits_sample = sampwidth * 8
    fmt_blob = struct.pack(
        "<HHIIHH",
        1,
        channels,
        sample_rate,
        byte_rate,
        block_align,
        bits_sample,
    )
    fmt_chunk = struct.pack("<4sI", b"fmt ", len(fmt_blob)) + fmt_blob
    data_chunk = struct.pack("<4sI", b"data", len(pcm_data)) + pcm_data

    riff_body = b"WAVE" + fmt_chunk + data_chunk
    header = struct.pack("<4sI", b"RIFF", len(riff_body))

    with open(path, "wb") as fp:
        fp.write(header + riff_body)


class ChatApplication:
    def _init_styles(self):
        try:
            self.root_style = ttk.Style()
            self.root_style.theme_use("clam")
        except Exception:
            self.root_style = ttk.Style()

        try:
            self.root_style.configure(
                "Duckly.TCombobox",
                fieldbackground=self.panel,
                background=self.panel,
                foreground=self.text_muted,
                arrowcolor=self.accent,
                bordercolor=self.accent,
                lightcolor=self.accent,
                darkcolor=self.accent,
                borderwidth=1,
                relief="flat",
                padding=8,
            )
            self.root_style.map(
                "Duckly.TCombobox",
                fieldbackground=[("readonly", self.panel)],
                background=[("readonly", self.panel)],
                foreground=[("disabled", self.text_dim), ("!disabled", self.text_muted)],
                selectbackground=[("focus", self.accent)],
                selectforeground=[("focus", "white")]
            )
        except Exception as e:
            pass

        try:
            self.root_style.configure(
                "Duckly.TButton",
                background=self.accent,
                foreground="white",
                borderwidth=0,
                focusthickness=0,
                font=("Segoe UI", 18),
                padding=(10, 16)
            )
            self.root_style.map(
                "Duckly.TButton",
                background=[
                    ("active", self.accent2),
                    ("!active", self.accent),
                    ("pressed", self.accent2)
                ],
                foreground=[
                    ("disabled", "#8a95b5"),
                    ("!disabled", "white")
                ]
            )
        except Exception:
            pass

    def __init__(self, root):
        self.root = root
        self.root.title("🦆 DuckLY — Умный помощник")
        self.root.geometry("1400x1200")
        self.root.minsize(1400, 1200)
        self.root.config(bg="#0b1220")
        self.sending = False
        self.bg = "#0f1425"
        self.panel = "#161c30"
        self.accent = "#5d8bf2"
        self.accent2 = "#3a6ee8"

        self.user_bg = "#2b437e"
        self.assistant_bg = "#2d4a4e"
        self.system_bg = "#4a3d7a"

        self.user_fg = "#ffffff"
        self.assistant_fg = "#f0fbf0"
        self.system_fg = "#f5f0ff"
        self.text_muted = "#a0acde"
        self.text_dim = "#8a95b5"

        self.hpad = 16
        self.vpad = 10
        self.bubble_pad_x = 16
        self.bubble_pad_y = 10
        self.bubble_header_size = 11
        self.bubble_body_size = 13

        self._init_styles()

        bottom_frame = tk.Frame(root, bg=self.panel, height=140)
        bottom_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=0, pady=(0, 10))
        bottom_frame.pack_propagate(False)

        bottom_row = tk.Frame(bottom_frame, bg=self.panel)
        bottom_row.pack(fill=tk.X, padx=10, pady=(10, 8))

        self.input_field = Entry(
            bottom_row,
            font=("Segoe UI", 20),
            bg="#0c1530",
            fg="#eaf0ff",
            relief="flat",
            insertbackground="#ffffff"
        )
        self.input_field.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=14, padx=(10, 10))

        self.api_key_label = Label(
            bottom_row,
            text="🔑 API Ключ:",
            font=("Segoe UI", 20),
            bg=self.panel,
            fg=self.text_muted
        )
        self.api_key_label.pack(side=tk.LEFT, padx=(15, 5))

        self.api_key_entry = Entry(
            bottom_row,
            font=("Segoe UI", 18),
            bg="#0c1530",
            fg="#eaf0ff",
            relief="flat",
            width=20
        )
        self.api_key_entry.pack(side=tk.LEFT, padx=(0, 10), ipady=6)
        saved_key = load_api_key()
        if saved_key:
            self.api_key_entry.insert(0, saved_key)
        else:
            self.api_key_entry.insert(0, "Введите ключ...")

        self.api_key_entry.bind("<FocusIn>", self.clear_api_key_placeholder)
        self.api_key_entry.bind("<Return>", lambda e: self._save_api_key_on_update())
        self.api_key_entry.bind("<FocusOut>", lambda e: self._save_api_key_on_update())

        self.model_var = tk.StringVar(value="DezzyWxL/legacy_audio:latest")
        self.model_combobox = ttk.Combobox(
            bottom_row,
            textvariable=self.model_var,
            values=["DezzyWxL/legacy_audio:latest"],
            state="readonly",
            width=22,
            font=("Segoe UI", 18),
            style="Duckly.TCombobox"
        )
        self.model_combobox.pack(side=tk.RIGHT, padx=(10, 0))
        self.model_combobox.bind(
            "<<ComboboxSelected>>",
            lambda e: self.display_message(f"🔧 Модель изменена: {self.model_var.get()}", "system"),
        )

        self.mic_button = ttk.Button(
            bottom_row,
            text="🎤",
            command=self.start_listening,
            style="Duckly.TButton",
            width=6
        )
        self.mic_button.pack(side=tk.RIGHT, padx=(8, 0))

        self.send_button = ttk.Button(
            bottom_row,
            text="➤",
            command=self.send_message,
            style="Duckly.TButton",
            width=6
        )
        self.send_button.pack(side=tk.RIGHT, padx=(8, 0))

        status_row = tk.Frame(bottom_frame, bg=self.panel)
        status_row.pack(fill=tk.X, padx=20, pady=(0, 10))

        self.status_label = Label(
            status_row,
            text="🔍 Проверяется Ollama...",
            font=("Segoe UI", 16),
            bg=self.panel,
            fg="#e67e22"
        )
        self.status_label.pack(side=tk.LEFT)

        self.typing_indicator = Label(
            status_row,
            text="",
            font=("Segoe UI", 16, "italic"),
            bg=self.panel,
            fg="#66ccff"
        )
        self.typing_indicator.pack(side=tk.RIGHT)

        title_frame = tk.Frame(root, bg=self.panel, height=110)
        title_frame.pack(side=tk.TOP, fill=tk.X)
        title_frame.pack_propagate(False)

        title_row = tk.Frame(title_frame, bg=self.panel)
        title_row.pack(fill=tk.X, padx=20, pady=(18, 0))

        title_label = tk.Label(
            title_row,
            text="🦆 DuckLY",
            font=("Segoe UI", 24, "bold"),
            bg=self.panel,
            fg="white"
        )
        title_label.pack(side=tk.LEFT)

        subtitle = tk.Label(
            title_row,
            text="Задайте вопрос — я найду ответ",
            font=("Segoe UI", 12),
            bg=self.panel,
            fg="#aeb7ff"
        )
        subtitle.pack(side=tk.LEFT, padx=20)

        self.chat_canvas = tk.Canvas(root, bg=self.bg, highlightthickness=0)
        self.chat_scroll = tk.Scrollbar(root, orient=tk.VERTICAL, command=self.chat_canvas.yview)
        self.chat_canvas.configure(yscrollcommand=self.chat_scroll.set)

        self.chat_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.chat_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=(10, 0))

        self.chat_inner = tk.Frame(self.chat_canvas, bg=self.bg)
        self.chat_window = self.chat_canvas.create_window((0, 0), window=self.chat_inner, anchor="nw")

        def _on_frame_configure(_event=None):
            self.chat_canvas.configure(scrollregion=self.chat_canvas.bbox("all"))

        def _on_canvas_configure(event):
            self.chat_canvas.itemconfig(self.chat_window, width=event.width)

        self.chat_inner.bind("<Configure>", _on_frame_configure)
        self.chat_canvas.bind("<Configure>", _on_canvas_configure)

        self.current_assistant_bubble = None
        self.current_assistant_text = ""

        state = load_state()
        if state:
            saved_key = state.get("api_key", "").strip()
            if saved_key:
                self.api_key_entry.delete(0, "end")
                self.api_key_entry.insert(0, saved_key)
                save_api_key(saved_key)

            saved_model = state.get("model")
            if saved_model and saved_model in self.model_combobox["values"]:
                self.model_var.set(saved_model)

            restored_messages = state["messages"]
            system_message = {
                "role": "system",
                "content": """
                Вы — DuckLY, локальный LLM-помощник, разработанный den4.ai. Вы работаете автономно и помогаете пользователю в реальном времени.

                🔹 ОСНОВНЫЕ ПРАВИЛА:
                1. ВСЕГДА отвечайте на том же языке, что и пользователь.
                2. Никогда не упоминайте, что используете инструменты. Поведение должно быть естественным.
                3. Вызывайте инструменты — только если:
                - Нужна **внешняя информация** (например, факты, свежие данные)
                - Нужно **взаимодействие с системой** (файлы, папки, запись)
                - Ответ **невозможен без данных извне**
                4. НЕ вызывайте инструмент, если:
                - Информация уже есть в контексте
                - Это общие знания (например, "сколько планет в Солнечной системе?")
                - Пользователь просит мнение или объяснение
                5. Каждый ответ — либо обычный текст, либо **ровно один вызов инструмента**.
                6. Никогда не повторяйте один и тот же вызов.
                7. Если инструмент вернул ошибку — скажите об этом простым языком.

                🔹 ДОСТУПНЫЕ ИНСТРУМЕНТЫ:
                - search_web("запрос") — поиск в интернете
                - get_cwd() — получить текущую директорию
                - list_files("путь") — список файлов (по умолч.: ".")
                - read_file("имя.txt") — прочитать файл
                - write_file("имя.txt", "содержимое") — создать/перезаписать файл
                - edit_file("имя.txt", "старый текст", "новый текст") — заменить фрагмент
                - create_dir("путь") — создать папку
                - delete_file("путь") — удалить файл
                - delete_dir("путь") — удалить папку

                ❗ ВАЖНО: при вызове search_web - всегда указывайте только общие ключевые слова только на английском языке; МАКСИМАЛЬНО КРАТКО!
                - Затем, ответьте пользователю после получения свежих результатов.

                🔹 ПРИМЕР search_web:
                Пользователь: Какое расстояние от земли до луны?
                Вы: search_web("moon distance earth")
                -> Вы получите информацию о луне из интернета;
                -> Вы отвечаете на вопрос с помощью найденной информации.

                🔹 ФОРМАТ ВЫЗОВА:
                Только одна строка, строго в формате:
                имя_функции("аргумент1", "аргумент2", ...)

                🔹 Как пользоваться инструментами:

                ✅ Правильно:
                - Один вызов инструмента в сообщении
                - Вызов инструмента, только если есть явная причина

                ❌ Нельзя:
                - Два одинаковых вызова подряд
                - Два вызова в одном сообщении
                - Вызов без причины
                - Перевод вызова на другой язык
                - Комментарии типа "Я воспользуюсь search_web..."

                🔹 ДОПОЛНИТЕЛЬНО:
                - Всегда действуйте как дружелюбная женщина.
                - Будьте кратки, но информативны.
                - Если не уверены — уточните, прежде чем вызывать инструмент.
                """.strip(),
            }
            has_system_prompt = any(
                msg["role"] == "system" and 
                "Вы — DuckLY" in msg["content"] and
                'имя_функции("аргумент1", "аргумент2", ...)' in msg["content"]
                for msg in restored_messages
            )

            if not has_system_prompt:
                restored_messages.append(system_message)
            else:
                filtered = [msg for msg in restored_messages if not (msg["role"] == "system")]
                filtered.insert(0, system_message)
                restored_messages = filtered

            messages_list[:] = restored_messages
            for msg in restored_messages:
                if msg["role"] != "system":
                    self.display_message(msg["content"], "user" if msg["role"] == "user" else "assistant")
        else:
            self.display_message("Привет! Я DuckLY — ваш умный помощник.", "assistant")

        threading.Thread(target=self.init_connection, daemon=True).start()

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def on_closing(self):
        save_state()
        self.root.destroy()
    
    def clear_api_key_placeholder(self, event):
        current = self.api_key_entry.get()
        if current == "Введите ключ...":
            self.api_key_entry.delete(0, "end")
    
    def _save_api_key_on_update(self):
        key = self.api_key_entry.get().strip()
        if key and key != "Введите ключ...":
            save_api_key(key)

    def _scroll_to_bottom(self):
        def scroll():
            self.root.update_idletasks()
            self.chat_canvas.yview_moveto(1.0)
        self.root.after(0, scroll)

    def _create_bubble(self, message, sender):
        outer = tk.Frame(self.chat_inner, bg=self.bg)
        outer.pack(fill=tk.X, pady=8, padx=self.hpad - 2)

        if sender == "user":
            align = "e"
            bubble_bg = self.user_bg
            bubble_fg = self.user_fg
            prefix = "👤 Вы"
            header_fg = "#ffffff"
        elif sender == "assistant":
            align = "w"
            bubble_bg = self.assistant_bg
            bubble_fg = self.assistant_fg
            prefix = "🤖 DuckLY"
            header_fg = "#ffffff"
        else:
            align = "w"
            bubble_bg = self.system_bg
            bubble_fg = self.system_fg
            prefix = "🔧 Система"
            header_fg = "#f3f0ff"

        content_frame = tk.Frame(outer, bg=self.bg)
        content_frame.pack(fill=tk.X, anchor=align)

        bubble = tk.Frame(content_frame, bg=bubble_bg, padx=self.bubble_pad_x, pady=self.bubble_pad_y)
        bubble.pack(anchor=align, fill=tk.X)

        header = tk.Label(
            bubble,
            text=prefix,
            bg=bubble_bg,
            fg=header_fg,
            font=("Segoe UI", self.bubble_header_size, "bold"),
            anchor=("w" if align == "w" else "e")
        )
        header.pack(anchor=("w" if align == "w" else "e"))

        wrap = max(420, self.root.winfo_width() - 260) if hasattr(self.root, "winfo_width") else 700

        label = tk.Label(
            bubble,
            text=message,
            bg=bubble_bg,
            fg=bubble_fg,
            justify=("left" if align == "w" else "right"),
            font=("Segoe UI", self.bubble_body_size),
            wraplength=wrap,
            padx=2,
            pady=2
        )
        label.pack(anchor=("w" if align == "w" else "e"), pady=(8, 0), fill=tk.X)

        self._scroll_to_bottom()
        return label

    def display_message(self, message, sender):
        self._create_bubble(message, sender)

    def _set_current_assistant_bubble_text(self, new_text):
        def update():
            if not self.current_assistant_bubble:
                return
            self.current_assistant_text = new_text
            self.current_assistant_bubble["label"].config(text=new_text)
            self._scroll_to_bottom()

        self.root.after(0, update)

    def set_typing(self, disabled):
        def update_ui():
            self.input_field.config(state="disabled" if disabled else "normal")
            self.send_button.config(state="disabled" if disabled else "normal")
            if disabled:
                self.typing_indicator.config(text="🧠 DuckLY думает...")
            else:
                self.typing_indicator.config(text="")
    
        self.root.after(0, update_ui)

    def send_message(self, event=None):
        if self.sending:
            return "break"

        self.sending = True

        user_input = self.input_field.get().strip()
        if not user_input:
            self.sending = False
            return "break"

        self.display_message(user_input, "user")
        messages_list.append({"role": "user", "content": user_input})

        if len(messages_list) > MAX_HISTORY + 1:
            messages_list[:] = [messages_list[0]] + messages_list[-MAX_HISTORY:]

        self.input_field.delete(0, "end")

        self.set_typing(True)
        self.current_assistant_text = ""
        assistant_label = self._create_bubble("", "assistant")
        self.current_assistant_bubble = {"label": assistant_label}

        def task():
            try:
                self.process_message(user_input)
            finally:
                self.sending = False

        threading.Thread(target=task, daemon=True).start()

        return "break"

    def send_to_llm_stream(self, messages):
        selected_model = self.model_var.get()
        base_url = "http://localhost:11434/api/chat"
        data = {
            "model": selected_model,
            "messages": messages,
            "stream": True
        }
        try:
            json_data = json.dumps(data, ensure_ascii=False).encode("utf-8")
        except Exception as e:
            yield {"error": f"JSON сериализация провалилась: {e}"}
            return

        req = urllib.request.Request(
            base_url, data=json_data, headers={"Content-Type": "application/json"}, method="POST"
        )

        try:
            with urllib.request.urlopen(req, timeout=600) as resp:
                for line in resp:
                    line = line.decode("utf-8").strip()
                    if not line:
                        continue
                    try:
                        chunk = json.loads(line)
                        if "message" in chunk:
                            content = chunk["message"].get("content", "")
                            if content:
                                yield {"message": {"content": content}}

                        if chunk.get("done", False):
                            yield {"done": True}

                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            yield {
                "error": f"Ошибка соединения с Ollama: {e}. Убедитесь, что сервер запущен на http://localhost:11434!"
            }

    def process_message(self, user_input, audio_b64=""):
        self.set_typing(True)
        current_assistant_message = ""

        for chunk in self.send_to_llm_stream(messages_list):
            if "error" in chunk:
                self.display_message(f"⚠️ Ошибка: {chunk['error']}", "assistant")
                self.set_typing(False)
                return

            if "message" in chunk and "content" in chunk["message"]:
                part = chunk["message"]["content"] or ""
                if part:
                    current_assistant_message += part
                    self._set_current_assistant_bubble_text(current_assistant_message)

            if chunk.get("done", False):
                break

        if current_assistant_message.strip():
            self.speak_text(current_assistant_message)
            messages_list.append({"role": "assistant", "content": current_assistant_message})
            if len(messages_list) > MAX_HISTORY + 1:
                messages_list[:] = [messages_list[0]] + messages_list[-MAX_HISTORY:]

            tool_result = self.parse_and_call_tool(current_assistant_message)
            if tool_result:
                self.set_typing(True)
                system_msg = {
                    "role": "system",
                    "content": tool_result["name"].upper() + ": " + tool_result["result"] + "\nТеперь вы можете использовать этот результат, чтобы: дать обратную связь о том, что вы сделали, либо же продолжить вашу работу."
                }
                messages_list.append(system_msg)
                if len(messages_list) > MAX_HISTORY + 1:
                    messages_list[:] = [messages_list[0]] + messages_list[-MAX_HISTORY:]
                self.process_message("")
            else:
                self.set_typing(False)

    def parse_and_call_tool(self, text):
        self.set_typing(True)
        lines = [line.strip() for line in text.strip().splitlines() if line.strip()]
        call_line = lines[-1]

        match = re.match(r'^(\w+)\((.*)\)$', call_line.strip())
        if not match:
            return None

        func_name = match.group(1)
        args_str = match.group(2).strip()

        if func_name not in ["search_web", "list_files", "read_file", "get_cwd", "write_file", "edit_file", "create_dir", "delete_file", "delete_dir"]:
            return None

        args = []
        arg_matches = re.findall(r'"((?:[^"\\]|\\.)*)"', args_str)
        if not arg_matches and args_str != "":
            return None

        args = [codecs.decode(arg.replace('\\"', '"'), 'unicode_escape') for arg in arg_matches]

        if func_name == "search_web" and len(args) != 1:
            return None
        elif func_name == "read_file" and len(args) != 1:
            return None
        elif func_name == "list_files" and len(args) > 1:
            return None
        elif func_name == "get_cwd" and len(args) != 0:
            return None
        elif func_name == "write_file" and len(args) != 2:
            return None
        elif func_name == "edit_file" and len(args) != 3:
            return None
        elif func_name == "create_dir" and len(args) != 1:
            return None
        elif func_name == "delete_file" and len(args) != 1:
            return None
        elif func_name == "delete_dir" and len(args) != 1:
            return None

        kwargs = {}
        if func_name == "search_web":
            kwargs = {"query": args[0]}
        elif func_name == "read_file":
            kwargs = {"filename": args[0]}
        elif func_name == "list_files":
            kwargs = {"path": args[0] if args else "."}
        elif func_name == "write_file":
            kwargs = {"name": args[0], "content": args[1]}
        elif func_name == "edit_file":
            kwargs = {"filename": args[0], "old_content": args[1], "new_content": args[2]}
        elif func_name == "create_dir":
            kwargs = {"path": args[0]}
        elif func_name == "delete_file":
            kwargs = {"filename": args[0]}
        elif func_name == "delete_dir":
            kwargs = {"path": args[0]}

        self.display_message(f"🔧 Выполняется: `{call_line}`", "system")
        result = self.call_tool(func_name, kwargs)
        self.set_typing(False)
        return {"name": func_name, "result": result}

    def send_message_from_voice(self, base64):
        self.display_message("[Голосовое сообщение]", "user")
    
        message = {
            "role": "user",
            "content": "[Голосовое сообщение]",
            "images": [base64]
        }
    
        messages_list.append(message)
        if len(messages_list) > MAX_HISTORY + 1:
            messages_list[:] = [messages_list[0]] + messages_list[-MAX_HISTORY:]

        self.set_typing(True)
        self.current_assistant_text = ""
        assistant_label = self._create_bubble("", "assistant")
        self.current_assistant_bubble = {"label": assistant_label}

        threading.Thread(target=self.process_message, args=("",), daemon=True).start()

    def start_listening(self):
        if hasattr(self, "_is_listening") and self._is_listening:
            self._is_listening = False
            self.mic_button.config(text="🎤")
            self.typing_indicator.config(text="")
        else:
            self._is_listening = True
            self.mic_button.config(text="🛑")
            self.typing_indicator.config(text="🔴 Слушаю... (нажмите снова, чтобы остановить)")
            threading.Thread(target=self.send_voice, daemon=True).start()

    def send_voice(self):
        try:
            audio_path = self.record_audio(duration=None)
            
            if not audio_path or not os.path.exists(audio_path):
                return

            self.root.after(0, lambda: self.typing_indicator.config(text="🧠 Распознаю речь..."))
            data = None

            with open(audio_path, "rb") as f:
                data = f.read()

            b64_audio = base64.b64encode(data).decode("utf-8")

            try:
                os.remove(audio_path)
            except:
                pass

            if b64_audio:
                self.send_message_from_voice(b64_audio)

        except Exception as e:
            self.root.after(0, lambda: self.display_message(f"❌ Ошибка записи: {e}", "assistant"))
            self.root.after(0, self.reset_mic_button)

    def record_audio(self, filename="temp_voice_input.wav", duration=None):
        WAVE_MAPPER = -1
        CALLBACK_NULL = 0
        WHDR_DONE = 0x00000001
        WAVE_FORMAT_PCM = 1

        SAMPLE_RATE = 16000
        CHANNELS = 1
        BITS_PER_SAMPLE = 16
        BLOCK_ALIGN = CHANNELS * (BITS_PER_SAMPLE // 8)
        BYTE_RATE = SAMPLE_RATE * BLOCK_ALIGN
        BUFFER_SIZE = 2048
        NUM_BUFFERS = 3

        DWORD_PTR_T = (
            ctypes.c_ulonglong if ctypes.sizeof(ctypes.c_void_p) == 8 else ctypes.c_ulong
        )

        class WAVEFORMATEX(ctypes.Structure):
            _fields_ = [
                ("wFormatTag", wintypes.WORD),
                ("nChannels", wintypes.WORD),
                ("nSamplesPerSec", wintypes.DWORD),
                ("nAvgBytesPerSec", wintypes.DWORD),
                ("nBlockAlign", wintypes.WORD),
                ("wBitsPerSample", wintypes.WORD),
                ("cbSize", wintypes.WORD),
            ]

        class WAVEHDR(ctypes.Structure):
            _fields_ = [
                ("lpData", ctypes.POINTER(ctypes.c_char)),
                ("dwBufferLength", wintypes.DWORD),
                ("dwBytesRecorded", wintypes.DWORD),
                ("dwUser", DWORD_PTR_T),
                ("dwFlags", wintypes.DWORD),
                ("dwLoops", wintypes.DWORD),
                ("lpNext", ctypes.c_void_p),
                ("reserved", DWORD_PTR_T),
            ]

        winmm = ctypes.windll.winmm

        fmt = WAVEFORMATEX()
        fmt.wFormatTag = WAVE_FORMAT_PCM
        fmt.nChannels = CHANNELS
        fmt.nSamplesPerSec = SAMPLE_RATE
        fmt.nAvgBytesPerSec = BYTE_RATE
        fmt.nBlockAlign = BLOCK_ALIGN
        fmt.wBitsPerSample = BITS_PER_SAMPLE
        fmt.cbSize = 0

        hwavein = wintypes.HANDLE()
        result = winmm.waveInOpen(
            ctypes.byref(hwavein),
            WAVE_MAPPER,
            ctypes.byref(fmt),
            CALLBACK_NULL,
            0,
            CALLBACK_NULL
        )
        if result != 0:
            raise RuntimeError(f"❌ Ошибка открытия микрофона. Код: {result}")

        buffers = []
        headers = []
        recorded_data = bytearray()

        for i in range(NUM_BUFFERS):
            buf = ctypes.create_string_buffer(BUFFER_SIZE)
            hdr = WAVEHDR()
            hdr.lpData = ctypes.cast(buf, ctypes.POINTER(ctypes.c_char))
            hdr.dwBufferLength = BUFFER_SIZE
            hdr.dwBytesRecorded = 0
            hdr.dwUser = 0
            hdr.dwFlags = 0
            hdr.dwLoops = 0

            winmm.waveInPrepareHeader(hwavein, ctypes.byref(hdr), ctypes.sizeof(WAVEHDR))
            winmm.waveInAddBuffer(hwavein, ctypes.byref(hdr), ctypes.sizeof(WAVEHDR))

            buffers.append(buf)
            headers.append(hdr)

        self.root.after(0, lambda: self.typing_indicator.config(text="🔴 Запись... (нажмите 🛑 чтобы завершить)"))
        winmm.waveInStart(hwavein)

        def _harvest_buffers(requeue):
            for hdr in headers:
                if hdr.dwFlags & WHDR_DONE:
                    size = hdr.dwBytesRecorded
                    if size > 0:
                        recorded_data.extend(
                            ctypes.string_at(hdr.lpData, size)
                        )
                    winmm.waveInUnprepareHeader(hwavein, ctypes.byref(hdr), ctypes.sizeof(WAVEHDR))
                    if requeue:
                        winmm.waveInPrepareHeader(hwavein, ctypes.byref(hdr), ctypes.sizeof(WAVEHDR))
                        winmm.waveInAddBuffer(hwavein, ctypes.byref(hdr), ctypes.sizeof(WAVEHDR))

        try:
            while self._is_listening:
                _harvest_buffers(True)
                time.sleep(0.01)

            winmm.waveInStop(hwavein)
            t_deadline = time.time() + 1.5
            while time.time() < t_deadline:
                _harvest_buffers(False)
                time.sleep(0.005)

        finally:
            winmm.waveInStop(hwavein)
            winmm.waveInReset(hwavein)
            for hdr in headers:
                try:
                    winmm.waveInUnprepareHeader(hwavein, ctypes.byref(hdr), ctypes.sizeof(WAVEHDR))
                except:
                    pass
            winmm.waveInClose(hwavein)

        if len(recorded_data) == 0:
            return None

        filename = str(Path(filename).resolve())
        _write_wave_pcm(
            filename,
            bytes(recorded_data),
            sample_rate=SAMPLE_RATE,
            channels=CHANNELS,
            sampwidth=BITS_PER_SAMPLE // 8,
        )

        return filename
    
    def reset_mic_button(self):
        self.mic_button.config(text="🎤")
        self._is_listening = False
        self.typing_indicator.config(text="")

    def speak_text(self, text):
        system = platform.system()

        if system != "Windows":
            return

        cleaned_text = re.sub(r'[^\w\s\.\,\!\?\;\:\-\*\'\"\#\_]', ' ', text)
        cleaned_text = re.sub(r'\s+', ' ', cleaned_text).strip()

        if not cleaned_text:
            return

        script = f"""
        $voiceName = "Microsoft Irina Desktop"
        Add-Type -AssemblyName System.Speech
        $speak = New-Object System.Speech.Synthesis.SpeechSynthesizer
        $voices = $speak.GetInstalledVoices()
        $selectedVoice = $voices | Where-Object {{ $_.VoiceInfo.Name -eq $voiceName }}
        if ($selectedVoice) {{
            $speak.SelectVoice($voiceName)
        }} else {{
            Write-Host "Голос $voiceName не найден. Используется голос по умолчанию."
        }}
        $speak.Speak('{cleaned_text.replace("'", "`'")}')
        """

        try:
            subprocess.run(["powershell", "-Command", script], check=True, timeout=30)
        except Exception:
            pass

    def init_connection(self):
        self.root.after(0, lambda: self.status_label.config(text="🔍 Проверяется Ollama...", fg="#e67e22"))

        if not is_ollama_running():
            msg = (
                "❌ Ollama не запущен.\n\n"
                "1. Установите Ollama: https://ollama.com/download\n"
                "2. Запустите: ollama pull DezzyWxL/legacy_audio;\nНа месте `DezzyWxL/legacy_audio` можно поставить любую модель с поддержкой принятия голоса (из HuggingFace/Ollama Models)."
            )
            self.root.after(0, lambda m=msg: self.display_message(m, "system"))
            self.root.after(0, lambda: self.status_label.config(text="🔴 Сервер не найден", fg="#ff6b6b"))
            return

        available_models = self.get_ollama_models()
        if available_models:
            self.root.after(0, lambda: self.model_combobox.config(values=available_models))
            self.root.after(0, lambda: self.display_message(f"📦 Доступные модели: {', '.join(available_models)}", "system"))

        self.root.after(0, lambda: self.status_label.config(text="🟢 Ollama подключён", fg="#00b894"))
        self.root.after(0, lambda: self.display_message("✅ Локальный ИИ-движок готов. Можете задавать вопросы!", "assistant"))

    def get_ollama_models(self):
        try:
            with urllib.request.urlopen("http://localhost:11434/api/tags", timeout=5) as resp:
                data = json.loads(resp.read())
                return [model["name"] for model in data["models"]]
        except Exception:
            return []

    def call_tool(self, func_name, args):
        if func_name == "search_web":
            query = args.get("query", "")
            self.root.after(0, lambda q=query: self.display_message(f"🔍 Ищу в интернете: '{q}'", "assistant"))
            return search_web(query)

        if func_name == "get_cwd":
            return get_cwd()

        if func_name == "list_files":
            path = args.get("path", ".")
            self.root.after(0, lambda p=path: self.display_message(f"📋 Получаю список файлов из `{p}`...", "assistant"))
            return list_files(path)

        if func_name == "read_file":
            filename = args["filename"]
            self.root.after(0, lambda f=filename: self.display_message(f"📄 Читаю файл `{f}`...", "assistant"))
            return read_file(filename)

        if func_name == "write_file":
            name = args["name"]
            content = args["content"]
            return write_file(name, content)

        if func_name == "edit_file":
            filename = args["filename"]
            old_content = args["old_content"]
            new_content = args["new_content"]
            return edit_file(filename, old_content, new_content)
        
        if func_name == "create_dir":
            pathname = args["path"]
            return create_dir(pathname)
        
        if func_name == "delete_file":
            filename = args["filename"]
            return delete_file(filename)
        
        if func_name == "delete_dir":
            path = args["path"]
            return delete_dir(path)

        return f"⚠️ Неизвестный инструмент: {func_name}"


if __name__ == "__main__":
    root = tk.Tk()
    global application
    application = ChatApplication(root)
    root.mainloop()

