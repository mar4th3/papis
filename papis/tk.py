
import tkinter as tk
import papis.config
import papis.utils
import re
import sys
import logging


class PapisWidget(tk.Misc):

    normal_mode = "normal"
    insert_mode = "insert"
    command_mode = "command"

    CURRENT_MODE = normal_mode

    def __init__(self):
        tk.Misc.__init__(self)
        self.logger = logging.getLogger(self.__class__.__name__)

    def get_mode(self):
        return PapisWidget.CURRENT_MODE

    def set_mode(self, mode):
        self.logger.debug("Mode -> %s" % mode)
        PapisWidget.CURRENT_MODE = mode

    def general_map(self, key, function, mode=None, recursive=False):
        def help_function(*args, **kwargs):
            if self.get_mode() == mode or mode is None:
                return function(*args, **kwargs)
        if recursive:
            self.bind_all(key, help_function)
        else:
            self.bind(key, help_function)

    def noremap(self, key, function, mode=None):
        self.general_map(key, function, mode, recursive=True)

    def norenmap(self, key, function):
        self.noremap(key, function, self.normal_mode)

    def noreimap(self, key, function):
        self.noremap(key, function, self.insert_mode)

    def norecmap(self, key, function):
        self.noremap(key, function, self.command_mode)

    def map(self, key, function, mode=None):
        self.general_map(key, function, mode, recursive=False)

    def nmap(self, key, function):
        self.map(key, function, self.normal_mode)

    def imap(self, key, function):
        self.map(key, function, self.insert_mode)

    def cmap(self, key, function):
        self.map(key, function, self.command_mode)

    def get_config(self, key, default):
        """Get user configuration

        :key: Key value
        :default: Default value

        """
        try:
            return papis.config.get(
                "tk-"+key, extras=[("tk-gui", "", key)]
            )
        except:
            return default


class Prompt(tk.Text,PapisWidget):


    def __init__(self, *args, **kwargs):
        tk.Text.__init__(self, *args, **kwargs)
        PapisWidget.__init__(self)
        self.bind("<Control-u>", self.clear)
        self.command = ""
        self.last_command = ""

    def changed(self):
        self.get_command()
        if self.last_command == self.command:
            return False
        else:
            return True

    def get_command(self):
        self.last_command = self.command
        if self.get_mode() == self.command_mode:
            self.command = self.get(1.0, tk.END)
        return self.command

    def echomsg(self, text):
        self.clear()
        self["height"] = len(text.split("\n"))-1
        self.insert(1.0, text)

    def clear(self, event=None):
        self["height"] = 1
        self.delete(1.0, tk.END)

    def focus(self, event=None):
        self.set_mode(self.command_mode)
        self.focus_set()


class Gui(tk.Tk,PapisWidget):

    index_draw_first = 0
    index_draw_last = 0
    key = None
    selected = None
    documents = []
    matched_indices = []
    documents_lbls = []
    index = 0
    entries_drawning = False

    def __init__(self):
        tk.Tk.__init__(self)
        PapisWidget.__init__(self)
        self.protocol("WM_DELETE_WINDOW", self.exit)
        self.geometry(
            "{}x{}".format(
                self.get_config("window-width", 900),
                self.get_config("window-height", 700),
            )
        )
        self["bg"] = self.get_config("window-bg", "#273238")
        self.bindings = [
            (self.get_config("focus_prompt", ":"), "focus_prompt"),
            (self.get_config("move_down", "j"), "move_down"),
            (self.get_config("move_up", "k"), "move_up"),
            (self.get_config("open", "o"), "open"),
            (self.get_config("edit", "e"), "edit"),
            (self.get_config("clear", "q"), "clear"),
            (self.get_config("move_top", "g"), "move_top"),
            (self.get_config("move_bottom", "<Shift-G>"), "move_bottom"),
            (self.get_config("help", "h"), "print_help"),
            (self.get_config("print_info", "i"), "print_info"),
            (self.get_config("exit", "<Control-q>"), "exit"),
            (self.get_config("half_down", "<Control-d>"), "half_down"),
            (self.get_config("half_up", "<Control-u>"), "half_up"),
            (self.get_config("scroll_down", "<Control-e>"), "scroll_down"),
            (self.get_config("scroll_up", "<Control-y>"), "scroll_up"),
            ("<Down>", "move_down"),
            ("<Up>", "move_up"),
            (self.get_config("autocomplete", "<Tab>"), "autocomplete"),
        ]
        self.title("Papis document manager")
        self.prompt = Prompt(
            self,
            bg=self.get_config("prompt-bg", "black"),
            borderwidth=-1,
            cursor="xterm",
            font="20",
            fg=self.get_config("prompt-fg", "lightgreen"),
            insertbackground=self.get_config("insertbackground", "red"),
            height=1
        )
        self.norecmap("<Return>", self.to_normal)
        self.nmap("<Return>", self.open)
        self.noremap("<Escape>", self.clear)
        self.noremap("<Control-l>", self.redraw_screen)
        self.cmap("<Control-c>", self.to_normal)
        self.map("<Configure>", self.on_resize)
        self.prompt.cmap("<KeyPress>", self.filter_and_draw)
        self.prompt.cmap("<Control-n>", self.move_down)
        self.prompt.cmap("<Control-p>", self.move_up)
        for bind in self.bindings:
            key = bind[0]
            name = bind[1]
            self.nmap(key, getattr(self, name))

    def get_matched_indices(self, force=False):
        if not self.prompt.changed() and not force:
            return self.matched_indices
        self.logger.debug("Indexing")
        command = self.prompt.get_command()
        match_format = self.get_config(
            "match_format", papis.config.get("match_format")
        )
        indices = list()
        for i, doc in enumerate(self.documents):
            if papis.utils.match_document(doc, command, match_format):
                indices.append(i)
        self.matched_indices = indices
        return indices

    def filter_and_draw(self, event=None):
        indices = self.get_matched_indices()
        self.undraw_documents_labels()
        self.draw_documents_labels(indices)

    def on_resize(self, event=None):
        pass

    def get_selected(self):
        return self.selected

    def get_selected_doc(self):
        return self.selected.doc

    def set_selected(self, doc_lbl):
        self.selected = doc_lbl

    def move(self, direction):
        indices = self.get_matched_indices()
        if direction == "down":
            if self.index < len(indices)-1:
                self.index += 1
        if direction == "up":
            if self.index > 0:
                self.index -= 1
        if self.index > self.index_draw_last-1:
            self.scroll_down()
        if self.index < self.index_draw_first:
            self.scroll_up()
        self.logger.debug(
            "index = %s in (%s , %s)"
            % (self.index, self.index_draw_first, self.index_draw_last)
        )
        self.draw_selection()

    def scroll(self, direction):
        self.undraw_documents_labels()
        if direction == "down":
            self.index_draw_first+=1
        else:
            if self.index_draw_first > 0:
                self.index_draw_first-=1
        self.update_selection_index()
        self.draw_documents_labels()

    def scroll_down(self, event=None):
        self.scroll("down")

    def scroll_up(self, event=None):
        self.scroll("up")

    def half_up(self, event=None):
        self.logger.debug("Half up")
        print("TODO")

    def half_down(self, event=None):
        self.logger.debug("Half down")
        print("TODO")

    def move_top(self, event=None):
        self.logger.debug("Moving to top")
        self.index_draw_first = 0
        self.index = self.index_draw_first
        self.redraw_documents_labels()

    def move_bottom(self, event=None):
        self.logger.debug("Moving to bottom")
        self.index_draw_first = len(self.get_matched_indices())-1
        self.index = self.index_draw_first
        self.redraw_documents_labels()

    def move_down(self, event=None):
        self.move("down")

    def move_up(self, event=None):
        self.move("up")

    def draw_selection(self, event=None):
        indices = self.get_matched_indices()
        if not len(indices):
            return False
        if self.get_selected() is not None:
            self.get_selected().configure(state="normal")
        self.update_selection_index()
        self.set_selected(self.documents_lbls[indices[self.index]])
        self.get_selected().configure(state="active")

    def set_documents(self, docs):
        self.documents = docs

    def to_normal(self, event=None):
        self.focus()
        self.set_mode(self.normal_mode)

    def clear(self, event=None):
        self.prompt.clear()
        self.to_normal()

    def autocomplete(self, event=None):
        pass

    def handle_return(self, event=None):
        command = self.prompt.get_command()
        self.prompt.clear()
        self.focus()

    def focus_prompt(self, event=None):
        self.prompt.clear()
        self.prompt.focus()

    def set_documents_labels(self):
        for doc in self.documents:
            self.documents_lbls.append(
                tk.Label(
                    text=self.get_config("header_format", "").format(doc=doc),
                    justify=tk.LEFT,
                    padx=10,
                    font=self.get_config("entry-font", "Times 14 normal"),
                    width=10*self.winfo_width(),
                    borderwidth=1,
                    pady=20,
                    fg=self.get_config("entry-fg", "grey77"),
                    anchor=tk.W,
                    activeforeground=self.get_config(
                        "activeforeground", "gray99"),
                    activebackground=self.get_config(
                        "activebackground", "#394249")
                )
            )
            setattr(self.documents_lbls[-1], "doc", doc)

    def redraw_documents_labels(self):
        self.undraw_documents_labels()
        self.draw_documents_labels()

    def undraw_documents_labels(self):
        if self.entries_drawning:
            return False
        if not len(self.documents_lbls):
            return False
        for doc in self.documents_lbls:
            doc.pack_forget()

    def redraw_screen(self, event=None):
        self.draw_documents_labels()

    def update_drawing_indices(self):
        primitive_height = self.documents_lbls[0].winfo_height()
        self.index_draw_last = self.index_draw_first +\
                int(self.winfo_height()/primitive_height)

    def update_selection_index(self):
        indices = self.get_matched_indices()
        if self.index < self.index_draw_first:
            self.index = self.index_draw_first
        if self.index > self.index_draw_last:
            self.index = self.index_draw_last-1
        if self.index > len(indices)-1:
            self.index = len(indices)-1

    def draw_documents_labels(self, indices=[]):
        if self.entries_drawning:
            return False
        else:
            self.logger.debug("Drawing")
            self.entries_drawning = True
        if not len(indices):
            indices = self.get_matched_indices()
        colors = (
            self.get_config(
                "entry-bg-1", self["bg"]),
            self.get_config(
                "entry-bg-2", self["bg"]),
        )
        self.update_drawing_indices()
        for i in range(self.index_draw_first, self.index_draw_last):
            if i >= len(indices):
                break
            doc = self.documents_lbls[indices[i]]
            doc["bg"] = colors[i%2]
            doc.pack(
                fill=tk.X
            )
        self.logger.debug("Drawing done")
        self.entries_drawning = False
        self.draw_selection()

    def main(self, documents):
        self.logger.debug("Packing prompt")
        self.prompt.pack(fill=tk.X, side=tk.BOTTOM)
        self.logger.debug("Setting docs")
        self.set_documents(documents)
        self.logger.debug("Creating labels")
        self.set_documents_labels()
        # force indexing
        self.logger.debug("Forcing indexing...")
        self.get_matched_indices(True)
        self.after(1,
            self.draw_documents_labels
        )
        self.after(200,
            self.update_drawing_indices
        )
        # self.after(2,
            # self.draw_selection()
        # )
        # self.after(2,
            # self.focus_prompt()
        # )
        return self.mainloop()

    def open(self, event=None):
        doc = self.get_selected_doc()
        papis.utils.open_file(
            doc.get_files()
        )

    def print_info(self, event=None):
        doc = self.get_selected_doc()
        self.prompt.echomsg(
            doc.dump()
        )

    def exit(self, event=None):
        self.logger.debug("Exiting")
        self.destroy()
        sys.exit(0)

    def edit(self, event=None):
        doc = self.get_selected_doc()
        papis.utils.general_open(
            doc.get_info_file(),
            "xeditor",
            default_opener="xterm -e vim",
            wait=True
        )
        doc.load()

    def print_help(self, event=None):
        text = ""
        for bind in self.bindings:
            text += "{key}  -  {name}\n".format(key=bind[0], name=bind[1])
        self.prompt.echomsg(text)
