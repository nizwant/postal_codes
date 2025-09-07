import camelot
import matplotlib.pyplot as plt

# Use interactive backend
plt.ion()  # interactive mode ON

tables = camelot.read_pdf("oficjalny_spis_pna_2025.pdf", flavor="stream", pages="3-22")

fig = camelot.plot(tables[0], kind="textedge")
plt.show()

# Keep the plot open
input("Press Enter to close...")
