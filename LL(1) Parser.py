import tkinter as tk
from tkinter import ttk, messagebox
from tkinter.scrolledtext import ScrolledText

# ================= GLOBALS =================
rules = []
grammar = {}
firsts = {}
follows = {}
nonterm_userdef = []
term_userdef = []

EPSILON = '#'
ENDMARK = '$'

# ================= PARSE TREE NODE =================
class ParseTreeNode:
    def __init__(self, symbol):
        self.symbol = symbol
        self.children = []

    def print_tree(self, prefix="", is_last=True):
        tree = prefix + ("└── " if is_last else "├── ") + self.symbol + "\n"
        new_prefix = prefix + ("    " if is_last else "│   ")
        for i, child in enumerate(self.children):
            tree += child.print_tree(new_prefix, i == len(self.children) - 1)
        return tree

# ================= GRAPHICAL TREE =================
def draw_parse_tree(root):
    win = tk.Toplevel()
    win.title("Graphical Parse Tree")
    win.geometry("1200x700")

    canvas = tk.Canvas(win, bg="white", scrollregion=(0, 0, 3000, 3000))
    canvas.pack(fill="both", expand=True)

    h_space, v_space = 90, 90

    def subtree_width(node):
        return 1 if not node.children else sum(subtree_width(c) for c in node.children)

    def draw_node(node, x, y):
        canvas.create_rectangle(x - 35, y - 20, x + 35, y + 20, fill="#E3ECFF")
        canvas.create_text(x, y, text=node.symbol, font=("Arial", 10, "bold"))

        start_x = x - (subtree_width(node) - 1) * h_space // 2
        for child in node.children:
            cw = subtree_width(child)
            cx = start_x + (cw - 1) * h_space // 2
            cy = y + v_space
            canvas.create_line(x, y + 20, cx, cy - 20, arrow=tk.LAST)
            draw_node(child, cx, cy)
            start_x += cw * h_space

    draw_node(root, 600, 60)

# ================= CORE LOGIC =================
def validateGrammarSymbols():
    for lhs in grammar:
        if lhs not in nonterm_userdef:
            raise ValueError(f"Undefined Non-Terminal: {lhs}")
        for prod in grammar[lhs]:
            for sym in prod:
                if sym != EPSILON and sym not in nonterm_userdef and sym not in term_userdef:
                    raise ValueError(f"Undefined Symbol: {sym}")

# ---------- LEFT RECURSION DETECTOR ----------
def detectLeftRecursion():
    def dfs(start, current, visited):
        if current in visited:
            return False
        visited.add(current)

        for prod in grammar[current]:
            first_sym = prod[0]
            if first_sym == start:
                return True
            if first_sym in grammar and dfs(start, first_sym, visited):
                return True
        return False

    for nt in grammar:
        if dfs(nt, nt, set()):
            raise ValueError(f"❌ Left recursion detected involving non-terminal: {nt}")

def computeAllFirsts():
    grammar.clear()
    firsts.clear()

    for rule in rules:
        lhs, rhs = rule.split("->")
        grammar[lhs.strip()] = [p.strip().split() for p in rhs.split("|")]

    validateGrammarSymbols()
    detectLeftRecursion()

    for nt in grammar:
        computeFirst(nt)

def computeFirst(symbol):
    if symbol in firsts:
        return firsts[symbol]

    if symbol not in grammar:
        return {symbol}

    firsts[symbol] = set()
    for prod in grammar[symbol]:
        if prod == [EPSILON]:
            firsts[symbol].add(EPSILON)
        else:
            for sym in prod:
                sym_first = computeFirst(sym)
                firsts[symbol].update(sym_first - {EPSILON})
                if EPSILON not in sym_first:
                    break
            else:
                firsts[symbol].add(EPSILON)
    return firsts[symbol]

def computeAllFollows():
    follows.clear()
    start = list(grammar.keys())[0]

    for nt in grammar:
        follows[nt] = set()
    follows[start].add(ENDMARK)

    changed = True
    while changed:
        changed = False
        for lhs in grammar:
            for prod in grammar[lhs]:
                for i, sym in enumerate(prod):
                    if sym in grammar:
                        before = len(follows[sym])
                        if i + 1 < len(prod):
                            nxt = prod[i + 1]
                            nxt_first = computeFirst(nxt)
                            follows[sym].update(nxt_first - {EPSILON})
                            if EPSILON in nxt_first:
                                follows[sym].update(follows[lhs])
                        else:
                            follows[sym].update(follows[lhs])
                        if len(follows[sym]) > before:
                            changed = True

def createParseTable():
    nts = list(grammar.keys())
    terms = term_userdef + [ENDMARK]
    table = [["" for _ in terms] for _ in nts]

    for A in grammar:
        for prod in grammar[A]:
            first_set = set()
            if prod == [EPSILON]:
                first_set = follows[A]
            else:
                for sym in prod:
                    sym_first = computeFirst(sym)
                    first_set.update(sym_first - {EPSILON})
                    if EPSILON not in sym_first:
                        break
                else:
                    first_set.update(follows[A])

            for t in first_set:
                r, c = nts.index(A), terms.index(t)
                if table[r][c]:
                    raise ValueError(f"❌ Grammar is NOT LL(1)\nConflict at M[{A},{t}]")
                table[r][c] = f"{A} → {' '.join(prod)}"

    return table, nts, terms

# ================= PARSER =================
def validateStringUsingStackBuffer(table, nts, terms, string, start):
    stack = [ENDMARK, start]
    buffer = string.split() + [ENDMARK]
    root = ParseTreeNode(start)
    node_stack = [None, root]
    steps = []

    while True:
        steps.append(f"Stack: {stack} | Buffer: {buffer}")
        top, cur = stack[-1], buffer[0]

        if top == cur == ENDMARK:
            steps.append("✔ STRING ACCEPTED")
            break

        if top == cur:
            stack.pop(); node_stack.pop(); buffer.pop(0)
        elif top in nts:
            entry = table[nts.index(top)][terms.index(cur)]
            if not entry:
                steps.append(f"❌ ERROR: No rule for ({top},{cur})")
                break
            stack.pop()
            parent = node_stack.pop()
            rhs = entry.split("→")[1].strip().split()
            if rhs != [EPSILON]:
                nodes = [ParseTreeNode(s) for s in rhs]
                parent.children = nodes
                for s, n in reversed(list(zip(rhs, nodes))):
                    stack.append(s); node_stack.append(n)
            else:
                parent.children.append(ParseTreeNode(EPSILON))
        else:
            steps.append("❌ ERROR: Terminal mismatch")
            break

    return steps, root

# ================= GUI =================
class LL1ParserGUI:
    def __init__(self, root):
        root.title("LL(1) Parser")
        root.geometry("1300x750")

        main = ttk.Frame(root); main.pack(fill="both", expand=True)
        left = ttk.Frame(main); left.pack(side="left", padx=10)
        right = ttk.Notebook(main); right.pack(fill="both", expand=True)

        ttk.Label(left, text="Grammar (# = epsilon)").pack()
        self.grammar = ScrolledText(left, width=40, height=10); self.grammar.pack()

        ttk.Label(left, text="Non-Terminals").pack()
        self.nt = ttk.Entry(left, width=40); self.nt.pack()

        ttk.Label(left, text="Terminals").pack()
        self.t = ttk.Entry(left, width=40); self.t.pack()

        ttk.Label(left, text="Input String").pack()
        self.string = ttk.Entry(left, width=40); self.string.pack()

        ttk.Button(left, text="Run LL(1) Parser", command=self.run).pack(pady=10)

        self.steps_tab = ScrolledText(right); right.add(self.steps_tab, text="Derivation")
        self.tree_tab = ScrolledText(right); right.add(self.tree_tab, text="Parse Tree")
        self.first_tab = ScrolledText(right); right.add(self.first_tab, text="FIRST Sets")
        self.follow_tab = ScrolledText(right); right.add(self.follow_tab, text="FOLLOW Sets")

        table_frame = ttk.Frame(right); right.add(table_frame, text="Parsing Table")
        self.parse_table = ttk.Treeview(table_frame, show="headings")
        self.parse_table.pack(fill="both", expand=True)

    def run(self):
        try:
            global rules, nonterm_userdef, term_userdef
            rules = self.grammar.get("1.0", tk.END).strip().split("\n")
            nonterm_userdef = [x.strip() for x in self.nt.get().split(",")]
            term_userdef = [x.strip() for x in self.t.get().split(",")]

            computeAllFirsts()
            computeAllFollows()
            table, nts, terms = createParseTable()

            self.parse_table["columns"] = ["NT"] + terms
            self.parse_table.delete(*self.parse_table.get_children())
            for col in ["NT"] + terms:
                self.parse_table.heading(col, text=col)
                self.parse_table.column(col, width=120, anchor="center")
            for i, nt in enumerate(nts):
                self.parse_table.insert("", "end", values=[nt] + table[i])

            steps, tree = validateStringUsingStackBuffer(table, nts, terms, self.string.get(), nts[0])
            self.steps_tab.delete("1.0", tk.END); self.steps_tab.insert(tk.END, "\n".join(steps))
            self.tree_tab.delete("1.0", tk.END); self.tree_tab.insert(tk.END, tree.print_tree())

            self.first_tab.delete("1.0", tk.END)
            for k, v in firsts.items():
                self.first_tab.insert(tk.END, f"FIRST({k}) = {v}\n")

            self.follow_tab.delete("1.0", tk.END)
            for k, v in follows.items():
                self.follow_tab.insert(tk.END, f"FOLLOW({k}) = {v}\n")

            draw_parse_tree(tree)

        except Exception as e:
            messagebox.showerror("Error", str(e))

# ================= RUN =================
if __name__ == "__main__":
    root = tk.Tk()
    LL1ParserGUI(root)
    root.mainloop()
