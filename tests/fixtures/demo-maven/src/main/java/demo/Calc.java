package demo;
public class Calc {
    int zeroSeen = 0;
    public boolean isPositive(int x) {
        if (x == 0) {
            zeroSeen++;
        }
        return x >= 0;   // BUG: zero is not positive
    }
}
