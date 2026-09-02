import math
# Creating prompt:
# in week1.py, write a script that prompts the user for an angle expressed in radians (limit the angles within one rotation of a circle) and returns to the     
# user what point on the unit circle it points to, in cartesian coordinates.      
def main():
    while True:
        try:
            angle = float(input("Enter an angle in radians (within one rotation of a circle): "))
            # Normalize angle to within one rotation [0, 2π)
            angle = angle % (2 * math.pi)
            # Compute cartesian coordinates on the unit circle
            x = math.cos(angle)
            y = math.sin(angle)
            print(f"The point on the unit circle is: ({x:.4f}, {y:.4f})")
            break
        except ValueError:
            print("Please enter a valid number.")

if __name__ == "__main__":
    main()
