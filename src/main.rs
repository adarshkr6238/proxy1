use tokio::net::{TcpListener, TcpStream};
use tokio::io::{copy_bidirectional};
use std::env;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let listen_addr = "0.0.0.0:7860";
    let target_addr = env::var("PROXY_TARGET").unwrap_or_else(|_| "api.telegram.org:443".to_string());

    let listener = TcpListener::bind(listen_addr).await?;
    println!("Listening on {}, proxying to {}", listen_addr, target_addr);

    loop {
        let (mut client_stream, _) = listener.accept().await?;
        let target_addr_clone = target_addr.clone();

        tokio::spawn(async move {
            let mut target_stream = TcpStream::connect(target_addr_clone).await.unwrap();
            let _ = copy_bidirectional(&mut client_stream, &mut target_stream).await;
        });
    }
}
