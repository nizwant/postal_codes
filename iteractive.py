import camelot
import matplotlib.pyplot as plt

# Use interactive backend
plt.ion()  # interactive mode ON

tables = camelot.read_pdf(
    "oficjalny_spis_pna_2025.pdf",
    flavor="hybrid",
    pages="3-22",
    table_areas=["28,813,567,27"],
    columns=["60,144,267,332,422,497"],
    row_tol=9,
    process_background=True,
)
camelot.plot(tables[1], kind="grid")
# camelot.plot(tables[-2], kind="grid")
plt.show()

# Keep the plot open
input("Press Enter to close...")
