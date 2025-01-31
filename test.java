import java.util.*;

public class Test{
    public static void main(String[] args){
        Set<Integer> set = new HashSet<Integer>();
        Scanner s = new Scanner(System.in);
        while (true){
            int i = s.nextInt();
            set.add(i);
            System.out.println(set);
        }
    }
}