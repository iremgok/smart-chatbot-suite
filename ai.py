import customtkinter as ctk
from tkinter import filedialog, messagebox
from openai import OpenAI
from threading import Thread
import xml.etree.ElementTree as ET
from setuptools.sandbox import save_path
from xmldiff import main, formatting
import openpyxl
from docx import Document
from reportlab.pdfgen import canvas
import shutil
import json
from PIL import Image, ImageDraw, ImageFont
import base64


class Help:
    def __init__(self, parent):
        self.help_win = ctk.CTkToplevel(parent)
        self.help_win.geometry("700x300")
        self.help_win.title("Help")
        self.help_win.attributes("-topmost", True)

        self.help_text = ctk.CTkTextbox(self.help_win)
        self.help_text.pack(fill="both", expand=True, padx=10, pady=10)

    def open_help(self):
        help_content = """
        XML Compare AI v1.0.0

        Developed by: İrem GÖK
        Contact: iremgk1803@gmail.com

        General Uses:
        - Chat using GPT-5.
        - Compare two XML files.
        - Use '+' button to select XML files.
        - Type messages and click 'Send'.
        - To create your file, write what you want inn the chatbox, click the download button and enter the file save path.
        """
        self.help_text.insert("end", help_content)
        self.help_text.configure(state="disabled")


# Chatbot File Class
class ChatBotFiles:
    def file_create(self, file_type, content_lines, save_path):
        if file_type == "txt":
            with open(save_path, "w", encoding="utf-8") as f:
                for line in content_lines:
                    f.write(line + "\n")

        elif file_type == "word":
            doc = Document()
            for line in content_lines:
                doc.add_paragraph(line)
            doc.save(save_path)

        elif file_type == "excel":
            wb = openpyxl.Workbook()
            ws = wb.active
            for i, line in enumerate(content_lines, start=1):
                ws[f"A{i}"] = line
            wb.save(save_path)

        elif file_type == "pdf":
            c = canvas.Canvas(save_path)
            y = 800
            for line in content_lines:
                c.drawString(100, y, str(line))
                y -= 20
            c.save()

        elif file_type == "png":
            img = Image.new("RGB", (800, 600), color = "white")
            draw = ImageDraw.Draw(img)
            font = ImageFont.load_default()
            y = 10
            for line in content_lines:
                draw.text((10, y), line, fill="black", font = font)
                y += 20
                img.save(save_path)

        else:
            return json.dumps({"file_type": file_type, "content_lines": content_lines, "error": "Unsupported file type!"})

        return save_path

    def download_file(self, file_path):
        save_path = filedialog.asksaveasfilename(initialfile=file_path)
        if save_path:
            shutil.copy(file_path, save_path)
            messagebox.showinfo("File saved", f"{file_path} → {save_path}")


class App:
    def __init__(self):
        self.root = ctk.CTk()
        self.root.title("AI Chatbot")
        self.root.geometry("800x600+400+100")

        self.client = OpenAI(api_key="YOUR_API_KEY")
        self.messages = [{"role": "system", "content": "You are a helpful assistant."}]
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("green")

        # Chatbox
        self.chatbox = ctk.CTkTextbox(self.root, width=650, height=350, state="disabled", wrap="word")
        self.chatbox.pack(fill="both", expand=True, pady=30, padx=10)

        # Frame for entry and buttons
        self.entry_frame = ctk.CTkFrame(self.root, corner_radius=10)
        self.entry_frame.pack(fill="x", pady=10, padx=10)


        self.user_entry = ctk.CTkEntry(self.entry_frame, width=500, placeholder_text="Write a message...")
        self.user_entry.pack(side="left", fill="x", expand=True, padx=(5,0))
        self.user_entry.bind("<Return>", lambda event: self.send_message())


        self.send_button = ctk.CTkButton(self.root, text="Send", command=self.send_message)
        self.send_button.pack(pady=5)


        self.help_button = ctk.CTkButton(self.root, text="Help", fg_color="transparent",
                                         text_color="green", hover_color="#2e2e2e",
                                         command=self.open_help_window)
        self.help_button.place(x=0, y=0)

        # '+' button for XML file selection
        self.xml_button = ctk.CTkButton(self.entry_frame, text="+", width=30, height=30,
                                        fg_color="transparent", text_color="green",
                                        hover_color="#2e2e2e", command=self.select_and_compare_files)
        self.xml_button.pack(side="right", padx=5)

        self.download_button = ctk.CTkButton(self.root, text="Create and Download", command=self.create_file_from_message)
        self.download_button.pack(pady=10)

        self.bot = ChatBotFiles()
        self.filepath = None

        self.root.mainloop()

    def write_to_chatbox(self, msg):
        self.chatbox.configure(state="normal")
        self.chatbox.insert("end", msg + "\n\n")
        self.chatbox.configure(state="disabled")
        self.chatbox.see("end")

    def send_message(self):
        user_input = self.user_entry.get()
        if not user_input.strip():
            return
        self.write_to_chatbox("You: " + user_input)
        self.user_entry.delete(0, "end")

        Thread(target=self.call_gpt, args=(user_input,)).start()

    def call_gpt(self, user_input):
        self.messages.append({"role": "user", "content": user_input})
        response = self.client.chat.completions.create(model="gpt-4o-mini", messages = self.messages)
        assistant_message = response.choices[0].message.content
        self.messages.append({"role": "assistant", "content": assistant_message})
        self.write_to_chatbox("GPT-5: " + assistant_message)

    def open_help_window(self):
        help_win = Help(self.root)
        help_win.open_help()

    def select_and_compare_files(self):
        file_names = filedialog.askopenfilenames(title="Select 2 XML files", filetypes=[("XML files", "*.xml")])
        if len(file_names) != 2:
            messagebox.showwarning("Warning", "Please select 2 files!")
            return

        file1, file2 = file_names
        self.write_to_chatbox(f"Files selected:\nFile 1: {file1}\nFile 2: {file2}\n")

        try:
            # Parse XML files
            tree1 = ET.parse(file1)
            tree2 = ET.parse(file2)

            # Get differences
            diffs = main.diff_files(file1, file2, formatter=formatting.XMLFormatter())
            if diffs:
                self.write_to_chatbox("Differences found between the files:")
                diffs_text = "\n".join([str(d) for d in diffs])

                prompt = f"The following XML file differences are summarized in a human-friendly way:\n{diffs_text}"
                response = self.client.chat.completions.create(
                    model="gpt-5",
                    messages=[{"role": "user", "content": prompt}]
                )
                summary = response.choices[0].message.content
                self.write_to_chatbox("Summary of differences:\n" + summary)
            else:
                self.write_to_chatbox("No differences found between the files.")

        except Exception as e:
            self.write_to_chatbox(f"Error comparing files: {e}")


    def create_file_from_message(self):
        user_message = self.user_entry.get()

        # GPT prompt
        prompt = f"""
        User message: "{user_message}"
        From this message, determine what type of file should be created. 
        Supported types are: txt, word, excel, pdf, png.
        - If the user wants to create an image, set "file_type" to "png".
        - For text-based files, provide each line of text in "content_lines".
        - For image files (png), provide simple text lines that will be drawn on the image in "content_lines".

        Respond only in JSON format exactly like this:
        {{ 
            "file_type": "...", 
            "content_lines": ["...", "..."] 
        }}
        Do not include any explanation or extra text.
        """

        response = self.client.chat.completions.create(
            model="gpt-5",
            messages=[{"role": "user", "content": prompt}] )

        gpt_reply = response.choices[0].message.content
        data = json.loads(gpt_reply)

        file_type = data["file_type"]
        content_lines = data["content_lines"]

        filetypes = [("Text File", "*.txt"),
                     ("Word Document", "*.docx"),
                     ("Excel Workbook", "*.xlsx"),
                     ("PDF File", "*.pdf"),
                     ("PNG Image", "*.png")]

        if file_type == "png":
            save_path = filedialog.asksaveasfilename(defaultextension=".png", filetypes = [("PNG Image", "*.png")])
            if save_path:
                response = self.client.images.generate(
                    model="gpt-image-1",
                    prompt = prompt,
                    size = "1024x1024")

                image_base64 = response.data[0].b64_json
                image_bytes = base64.b64decode(image_base64)
                with open(save_path, "wb") as f:
                    f.write(image_bytes)
                messagebox.showinfo("Success", "Image saved to " + save_path)

        else:
            file_ext = {"txt": ".txt", "word": ".docx", "pdf": ".pdf", "png": ".png"}.get(file_type, "")

            filetypes_sorted = [t for t in filetypes if t[1] == f"*{file_ext}"] + [t for t in filetypes if t[1] != f"*{file_ext}"]

            if file_type in ["txt", "word", "excel", "pdf", "png"]:

                save_path = filedialog.asksaveasfilename(defaultextension=file_ext, filetypes = filetypes_sorted)

                if save_path:
                    self.bot.file_create(file_type, content_lines, save_path)
                    messagebox.showinfo("Successful", f"File created at: {save_path}")
            else:
                messagebox.showerror("Warning", "Unsupported file type!")


if __name__ == "__main__":
    App()
