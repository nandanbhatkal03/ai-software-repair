package demo;
import org.junit.Test;
import static org.junit.Assert.*;
public class CalcTest {
    @Test public void testPos()  { assertTrue(new Calc().isPositive(5)); }
    @Test public void testNeg()  { assertFalse(new Calc().isPositive(-1)); }
    @Test public void testZero() { assertFalse(new Calc().isPositive(0)); }
}
