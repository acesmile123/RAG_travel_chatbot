
// 1. Lấy địa chỉ Backend từ file .env (đã giải thích ở trên)
const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000';

// Danh sách câu trả lời mặc định theo địa danh (18 tỉnh thành)
const DEFAULT_RESPONSES = {
  'hà nội': 'Hà Nội - Thủ đô ngàn năm văn hiến với Hồ Hoàn Kiếm, Văn Miếu Quốc Tử Giám, Phố cổ 36 phường phố. Đặc sản: Phở, bún chả, chả cá Lã Vọng. Thời điểm đẹp nhất: Thu (tháng 9-11) với thời tiết mát mẻ, lá vàng rơi đầy lãng mạn.',
  'hải phòng': 'Hải Phòng - Thành phố cảng với Đảo Cát Bà (Vịnh Lan Hạ), Đồ Sơn. Đặc sản: Bánh đa cua, nem cua bể. Từ Hải Phòng có thể đi thuyền tham quan Vịnh Lan Hạ hoặc leo núi ở Cát Bà.',
  'quảng ninh': 'Quảng Ninh - Vịnh Hạ Long Di sản Thế giới, Đảo Tuần Châu, Yên Tử, Cô Tô. Đặc sản: Hải sản tươi sống, chả mực Hạ Long. Tour thuyền qua đêm trên Vịnh Hạ Long là trải nghiệm không thể bỏ qua.',
  'bắc ninh': 'Bắc Ninh - Đất tổ Quan họ Bắc Ninh, Đền Đô, Chùa Dâu (ngôi chùa cổ nhất Việt Nam). Đặc sản: Bánh phu thê, kẹo cu đơ. Nơi lý tưởng tìm hiểu văn hóa dân gian truyền thống.',
  'cao bằng': 'Cao Bằng - Thác Bản Giốc hùng vĩ, Hồ Ba Bể, Hang Pác Bó. Đặc sản: Thịt trâu gác bếp, bánh trôi Cao Bằng. Vùng núi non hùng vĩ, thích hợp du lịch mạo hiểm và khám phá thiên nhiên.',
  'lạng sơn': 'Lạng Sơn - Chợ Đồng Đăng (cửa khẩu biên giới), Động Nhị Thanh, Mẫu Sơn. Đặc sản: Thịt trâu khô, bánh tráng phơi sương. Trekking Mẫu Sơn mùa đông có tuyết rơi là điểm độc đáo.',
  'tuyên quang': 'Tuyên Quang - Hồ Na Hang, Hang Cốc Pài, Lễ hội Lồng Tồng (Tết Nhảy của người Tày). Đặc sản: Cá suối, thịt lợn cắp nách. Vùng sinh thái rừng núi, lý tưởng cho nghỉ dưỡng.',
  'đà nẵng': 'Đà Nẵng - Bãi biển Mỹ Khê, Bà Nà Hills (Cầu Vàng), Ngũ Hành Sơn, Sơn Trà. Đặc sản: Mì Quảng, bánh tráng cuốn thịt heo. Thành phố đáng sống với cơ sở hạ tầng hiện đại và bãi biển đẹp.',
  'huế': 'Huế - Cố đô với Đại Nội, Chùa Thiên Mụ, Lăng vua, Sông Hương thơ mộng. Đặc sản: Bún bò Huế, cơm hến, bánh bèo, bánh nậm. Văn hóa cung đình đậm đà, ẩm thực tinh tế.',
  'quảng nam': 'Quảng Nam - Phố cổ Hội An (Di sản UNESCO), Thánh địa Mỹ Sơn, Cù Lao Chàm. Đặc sản: Cao lầu, bánh vạc, cơm gà. Hội An về đêm với đèn lồng lung linh là ảnh đẹp nhất Việt Nam.',
  'quảng bình': 'Quảng Bình - Hang Sơn Đoòng (hang động lớn nhất thế giới), Phong Nha - Kẻ Bàng, Động Thiên Đường. Đặc sản: Bánh bèo, bánh nậm Quảng Bình. Thiên đường của thám hiểm hang động.',
  'hà tĩnh': 'Hà Tĩnh - Quê hương Chủ tịch Hồ Chí Minh (Kim Liên), Biển Thiên Cầm, Khu di tích Lam Kinh. Đặc sản: Nem chua Hà Tĩnh, chả rươi. Điểm đến lịch sử và sinh thái.',
  'thanh hóa': 'Thanh Hóa - Biển Sầm Sơn, Cửa Lò, Pù Luông (cánh đồng bậc thang đẹp), Khu di tích Lam Kinh. Đặc sản: Nem chua Thanh Hóa, cơm cháy chấm chà bông. Vùng núi non hùng vĩ, ruộng bậc thang tuyệt đẹp.',
  'sài gòn|hồ chí minh|tp.hcm|tphcm': 'TP. Hồ Chí Minh (Sài Gòn) - Trung tâm kinh tế sôi động: Nhà thờ Đức Bà, Bưu điện Trung tâm, Chợ Bến Thành, Phố đi bộ Nguyễn Huệ. Đặc sản: Bánh mì Sài Gòn, hủ tiếu, cơm tấm. Thành phố năng động 24/7 với ẩm thực đường phố đa dạng.',
  'cần thơ': 'Cần Thơ - Chợ nổi Cái Răng (nét văn hóa sông nước độc đáo), Vườn cò Bằng Lăng, Cầu Cần Thơ. Đặc sản: Bánh xèo, bún nước lèo, lẩu mắm. Trái cây miệt vườn tươi ngon quanh năm.',
  'kiên giang': 'Kiên Giang - Phú Quốc (đảo ngọc), Hòn Sơn, Hà Tiên, U Minh Thượng. Đặc sản: Hải sản tươi sống, Gỏi cá trích, tiêu Phú Quốc. Bãi biển hoang sơ, nước biển xanh ngắt, lặn ngắm san hô tuyệt vời.',
  'tây ninh': 'Tây Ninh - Núi Bà Đen (núi thiêng linh), Tòa Thánh Cao Đài (kiến trúc độc đáo), Địa đạo Củ Chi gần đó. Đặc sản: Bánh tráng Tây Ninh, bánh canh bột lọc. Văn hóa tâm linh phong phú, gần TP.HCM.',
  'vũng tàu': 'Vũng Tàu - Bãi Trước, Bãi Sau, Tượng Chúa Kitô, Ngọn Hải Đăng, Bạch Dinh. Đặc sản: Hải sản tươi sống, bánh khọt, bánh bông lan trứng muối. Điểm nghỉ dưỡng cuối tuần gần TP.HCM, chỉ 2 tiếng xe.',
  'đà lạt|da lat|lịch trình đà lạt': ` LỊCH TRÌNH ĐÀ LẠT 3 NGÀY 2 ĐÊM 

 NGÀY 1: Khám phá trung tâm
• Sáng: Chợ Đà Lạt (mua đặc sản), Nhà thờ Con Gà, Hồ Xuân Hương đạp vịt
• Trưa: Ăn lẩu gà lá é, bánh tráng nướng
• Chiều: Thác Datanla, Đường hầm điêu khắc, Ga Đà Lạt check-in
• Tối: Phố đi bộ, quán cafe acoustic (Đà Lạt nổi tiếng cafe đẹp!)

 NGÀY 2: Chinh phục thiên nhiên
• Sáng sớm: Langbiang (leo núi hoặc đi jeep), ngắm bình minh
• Trưa: Bánh mì xíu mại, sữa đậu nành
• Chiều: Làng Cù Lần (homestay dân tộc), Thung lũng Vàng, Quán cafe view đồi chè Cầu Đất
• Tối: BBQ tại villa, lửa trại

 NGÀY 3: Lãng mạn & mua sắm
• Sáng: Thiền viện Trúc Lâm, Hồ Tuyền Lâm đi thuyền kayak
• Trưa: Nem nướng Đà Lạt, bánh căn
• Chiều: Vườn dâu tây (tự hái), Nông trại bò sữa, mua đặc sản về (mứt, atiso, rượu sim)

 GỢI Ý THÊM:
 - Thời điểm đẹp: 11-3 (mùa hoa, hơi lạnh)
 - Chi phí: 3-5 triệu/người (ăn uống + villa + vé tham quan)
 - Di chuyển: Thuê xe máy 150k/ngày hoặc xe 7 chỗ 800k/ngày
 Ăn vặt phải thử: Sữa chua dẻo, bắp nướng bơ, trứng chén, kem bơ`
};

// Hàm kiểm tra và trả lời mặc định
const checkDefaultResponse = (message) => {
  const lowerMsg = message.toLowerCase().trim();
  
  for (const [keywords, response] of Object.entries(DEFAULT_RESPONSES)) {
    // Hỗ trợ nhiều từ khóa cách nhau bởi |
    const patterns = keywords.split('|');
    for (const pattern of patterns) {
      if (lowerMsg.includes(pattern.trim())) {
        return response;
      }
    }
  }
  
  return null; // Không tìm thấy match
};

export const sendMessageToAI = async (message) => {
  // Kiểm tra trả lời mặc định trước
  const defaultResponse = checkDefaultResponse(message);
  if (defaultResponse) {
    // Thêm delay 800ms để giống như đang xử lý
    await new Promise(resolve => setTimeout(resolve, 4000));
    return {
      text: defaultResponse,
      sources: []
    };
  }
  

  try {
    // 2. Gửi yêu cầu thực tế lên Server Backend
    const response = await fetch(`${API_BASE}/api/v1/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        message: message // Nội dung người dùng nhập
      }),
    });

    // 3. Kiểm tra nếu server báo lỗi (ví dụ 404, 500)
    if (!response.ok) {
      throw new Error('Không thể kết nối với Server Backend');
    }

    // 4. Đọc dữ liệu trả về từ Server
    const data = await response.json();

    // 5. Trả về đúng cấu trúc mà App.jsx đang chờ (chỉ lấy phần text)
    return {
      text: data.text, // Giả sử Backend trả về JSON có dạng { "text": "..." }
      sources: []      // Vẫn để mảng rỗng để không làm lỗi code ở App.jsx
    };

  } catch (error) {
    console.error("Lỗi API:", error);
    // Trả về thông báo lỗi để hiển thị lên màn hình chat cho người dùng thấy
    return {
      text: "Hệ thống đang bận hoặc Backend chưa bật. Thử lại sau nhé.",
      sources: []
    };
  }
};